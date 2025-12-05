from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime, date
import requests
from bs4 import BeautifulSoup
from .models import B3Rate


def fetch_b3_rates(date):
    """
    Fetch rates from B3 website for a given date.
    Returns a list of dictionaries with indicator and value.
    """
    try:
        # Format date for B3 API (DD/MM/YYYY)
        formatted_date = date.strftime('%d/%m/%Y')
        
        # B3 API endpoint
        url = 'https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/consultas/mercado-de-derivativos/precos-referenciais/taxas-referenciais-bm-fbovespa/'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try to fetch the page with the date parameter
        params = {'data': formatted_date}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse the rates from the page
            rates = []
            
            # Look for tables containing the rates
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header row
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        indicator = cols[0].get_text(strip=True)
                        value_text = cols[1].get_text(strip=True)
                        
                        # Clean and convert value
                        try:
                            # Remove % signs and convert comma to dot
                            value_clean = value_text.replace('%', '').replace(',', '.').strip()
                            value = float(value_clean)
                            
                            if indicator and value:
                                rates.append({
                                    'indicator': indicator,
                                    'value': value
                                })
                        except (ValueError, AttributeError):
                            continue
            
            return rates
        else:
            return []
            
    except Exception as e:
        print(f"Error fetching B3 rates: {e}")
        return []


def homepage(request):
    """
    Homepage view with date picker to fetch B3 rates.
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
                            indicator=rate_data['indicator'],
                            value=rate_data['value']
                        )
                        rate_objects.append(rate_obj)
                    
                    B3Rate.objects.bulk_create(rate_objects, ignore_conflicts=True)
                    
                    # Retrieve from database to display
                    context['rates'] = B3Rate.objects.filter(date=selected_date)
                    context['message'] = f'Taxas obtidas da B3 e salvas no banco de dados. {len(fetched_rates)} taxas encontradas.'
                else:
                    context['error'] = 'Nenhuma taxa encontrada para esta data no site da B3.'
                    
        except ValueError:
            context['error'] = 'Data inválida. Use o formato correto.'
        except Exception as e:
            context['error'] = f'Erro ao processar: {str(e)}'
    
    return render(request, 'rates/homepage.html', context)

