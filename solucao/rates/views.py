from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import requests
from bs4 import BeautifulSoup
from .models import B3Rate


RATES_PAGE_URL = (
    "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/"
    "lum-taxas-referenciais-bmf-ptBR.asp"
)
RATE_SERIES_CODE = "PRE"


def normalize_cell_text(cell) -> str:
    """Normalize cell text by removing extra whitespace."""
    return cell.get_text(" ", strip=True).replace("\xa0", " ")


def parse_ptbr_decimal(text: str):
    """Parse Brazilian decimal format '14,90' -> Decimal('14.90')."""
    t = text.strip()
    if not t:
        return None
    # Remove thousands separators (.) and swap decimal comma
    t = t.replace(".", "").replace(",", ".")
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def read_table_grid(table, default_cols: int = 3):
    """Return a rectangular grid of strings, expanding rowspan/colspan."""
    grid = []
    pending_rowspans = {}

    def fill_pending(row, col):
        while col in pending_rowspans:
            text, remaining = pending_rowspans[col]
            row.append(text)
            remaining -= 1
            if remaining:
                pending_rowspans[col] = (text, remaining)
            else:
                pending_rowspans.pop(col)
            col += 1
        return col

    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue

        row = []
        col = 0
        for cell in cells:
            col = fill_pending(row, col)
            text = normalize_cell_text(cell)

            rowspan = int(cell.get("rowspan", 1) or 1)
            colspan = int(cell.get("colspan", 1) or 1)

            for i in range(colspan):
                row.append(text)
                if rowspan > 1:
                    pending_rowspans[col + i] = (text, rowspan - 1)
            col += colspan

        grid.append(row)

    # Handle any loose cells not in <tr>
    ncols = len(grid[0]) if grid else default_cols
    loose_cells = [c for c in table.find_all(["th", "td"]) if c.find_parent("tr") is None]
    for i in range(0, len(loose_cells), ncols):
        row = [normalize_cell_text(c) for c in loose_cells[i : i + ncols]]
        row += [""] * (ncols - len(row))
        grid.append(row)

    width = max((len(r) for r in grid), default=0)
    for r in grid:
        r += [""] * (width - len(r))

    return grid


def extract_di_pre_curve_points(table_grid):
    """
    Extract DI x PRE curve points from table grid.
    Expected columns:
      - col 0: DI x pré 252
      - col 1: DI x pré 360
      - col 2: Dias Corridos
    """
    points = []

    for row in table_grid:
        if len(row) < 3:
            continue

        di_pre_252_text, di_pre_360_text, dias_corridos_text = row[0], row[1], row[2]
        if not dias_corridos_text.strip().isdigit():
            continue

        dias_corridos = int(dias_corridos_text.strip())
        di_pre_252 = parse_ptbr_decimal(di_pre_252_text)
        di_pre_360 = parse_ptbr_decimal(di_pre_360_text)

        if di_pre_252 is None or di_pre_360 is None:
            continue

        points.append({
            'dias_corridos': dias_corridos,
            'di_pre_252': di_pre_252,
            'di_pre_360': di_pre_360,
        })

    return points


def fetch_b3_rates(target_date):
    """
    Fetch DI x PRE rates from B3 website for a given date.
    Returns a list of dictionaries with dias_corridos, di_pre_252, and di_pre_360.
    """
    try:
        # Format date for B3 (DD/MM/YYYY and YYYYMMDD)
        date_br = target_date.strftime('%d/%m/%Y')
        date_yyyymmdd = target_date.strftime('%Y%m%d')
        
        # Request parameters
        form_fields = {
            "slcTaxa": RATE_SERIES_CODE,
            "Data1": date_yyyymmdd,
            "Data": date_br,
            "convertexls1": "",
            "nomexls": "",
            "lQtdTabelas": "",
            "IDIOMA": "1",
        }
        query_params = {
            "Data": date_br,
            "Data1": date_yyyymmdd,
            "slcTaxa": RATE_SERIES_CODE,
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": RATES_PAGE_URL,
        }
        
        response = requests.post(
            RATES_PAGE_URL,
            params=query_params,
            data=form_fields,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, "lxml")
        main_rates_table = soup.select_one("#tb_principal1")
        
        if not main_rates_table:
            return []
        
        table_grid = read_table_grid(main_rates_table)
        rates = extract_di_pre_curve_points(table_grid)
        
        return rates
            
    except Exception as e:
        print(f"Error fetching B3 rates: {e}")
        return []


def homepage(request):
    """
    Homepage view with date picker to fetch B3 DI x PRE rates.
    """
    context = {
        'rates': None,
        'selected_date': None,
        'error': None,
        'today': date.today()
    }
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        
        try:
            # Parse the date
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            context['selected_date'] = selected_date
            
            # Check if rates exist in database
            existing_rates = B3Rate.objects.filter(date=selected_date)
            
            if existing_rates.exists():
                # Rates found in database
                context['rates'] = existing_rates
                context['message'] = 'Taxas encontradas no banco de dados.'
            else:
                # Fetch from B3 website
                fetched_rates = fetch_b3_rates(selected_date)
                
                if fetched_rates:
                    # Save to database
                    rate_objects = []
                    for rate_data in fetched_rates:
                        rate_obj = B3Rate(
                            date=selected_date,
                            dias_corridos=rate_data['dias_corridos'],
                            di_pre_252=rate_data['di_pre_252'],
                            di_pre_360=rate_data['di_pre_360']
                        )
                        rate_objects.append(rate_obj)
                    
                    B3Rate.objects.bulk_create(rate_objects, ignore_conflicts=True)
                    
                    # Retrieve from database to display
                    context['rates'] = B3Rate.objects.filter(date=selected_date)
                    context['message'] = f'Taxas DI x PRÉ obtidas da B3 e salvas no banco de dados. {len(fetched_rates)} pontos da curva encontrados.'
                else:
                    context['error'] = 'Nenhuma taxa encontrada para esta data no site da B3.'
                    
        except ValueError:
            context['error'] = 'Data inválida. Use o formato correto.'
        except Exception as e:
            context['error'] = f'Erro ao processar: {str(e)}'
    
    return render(request, 'rates/homepage.html', context)

