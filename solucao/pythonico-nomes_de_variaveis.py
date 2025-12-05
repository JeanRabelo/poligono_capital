#!/usr/bin/env python3
from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import requests
from bs4 import BeautifulSoup

RATES_PAGE_URL = (
    "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/"
    "lum-taxas-referenciais-bmf-ptBR.asp"
)

# Reference date used by the page (two formats are required by the endpoint)
REFERENCE_DATE_BR = "01/12/2025"       # dd/mm/yyyy
REFERENCE_DATE_YYYYMMDD = "20251201"   # yyyymmdd

# "PRE" is what the site expects in slcTaxa for this table
RATE_SERIES_CODE = "PRE"

REQUEST_FORM_FIELDS = {
    "slcTaxa": RATE_SERIES_CODE,
    "Data1": REFERENCE_DATE_YYYYMMDD,
    "Data": REFERENCE_DATE_BR,
    "convertexls1": "",
    "nomexls": "",
    "lQtdTabelas": "",
    "IDIOMA": "1",
}
REQUEST_QUERY_PARAMS = {
    "Data": REFERENCE_DATE_BR,
    "Data1": REFERENCE_DATE_YYYYMMDD,
    "slcTaxa": RATE_SERIES_CODE,
}
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": RATES_PAGE_URL,
}

def normalize_cell_text(cell) -> str:
    return cell.get_text(" ", strip=True).replace("\xa0", " ")

def read_table_grid(table, default_cols: int = 3) -> list[list[str]]:
    """Return a rectangular grid of strings, expanding rowspan/colspan."""
    grid: list[list[str]] = []
    pending_rowspans: dict[int, tuple[str, int]] = {}

    def fill_pending(row: list[str], col: int) -> int:
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

        row: list[str] = []
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

    # Handle any "loose" cells not in <tr> (rare, but your original handled it)
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

def parse_ptbr_decimal(text: str) -> Decimal | None:
    """Parse '14,90' -> Decimal('14.90'). Returns None if not a number."""
    t = text.strip()
    if not t:
        return None
    # remove thousands separators (.) and swap decimal comma
    t = t.replace(".", "").replace(",", ".")
    try:
        return Decimal(t)
    except InvalidOperation:
        return None

@dataclass(frozen=True)
class DiPreCurvePoint:
    dias_corridos: int
    di_pre_252: Decimal
    di_pre_360: Decimal

def extract_di_pre_curve_points(table_grid: list[list[str]]) -> list[DiPreCurvePoint]:
    """
    Based on your output mapping:
      - col 0: DI x pré 252 (e.g., 14,90)
      - col 1: DI x pré 360 (e.g., 0,00 / 15,23 / ...)
      - col 2: Dias Corridos (e.g., 1, 7, 11, ...)
    """
    points: list[DiPreCurvePoint] = []

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

        points.append(
            DiPreCurvePoint(
                dias_corridos=dias_corridos,
                di_pre_252=di_pre_252,
                di_pre_360=di_pre_360,
            )
        )

    return points

def main() -> int:
    response = requests.post(
        RATES_PAGE_URL,
        params=REQUEST_QUERY_PARAMS,
        data=REQUEST_FORM_FIELDS,
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, "lxml")
    main_rates_table = soup.select_one("#tb_principal1")
    if not main_rates_table:
        print("rates table not found (#tb_principal1)", file=sys.stderr)
        return 1

    table_grid = read_table_grid(main_rates_table)
    di_pre_curve_points = extract_di_pre_curve_points(table_grid)

    # "Same information" output, but now explicitly tied to domain names:
    print("dias_corridos\tdi_pre_252\tdi_pre_360")
    for p in di_pre_curve_points:
        # keep Brazilian formatting in output if you want:
        di252 = str(p.di_pre_252).replace(".", ",")
        di360 = str(p.di_pre_360).replace(".", ",")
        print(f"{p.dias_corridos}\t{di252}\t{di360}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
