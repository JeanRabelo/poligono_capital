#!/usr/bin/env python3
import csv
import sys
import requests
from bs4 import BeautifulSoup

URL = "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-taxas-referenciais-bmf-ptBR.asp"

PARAMS = {"Data": "01/12/2025", "Data1": "20251201", "slcTaxa": "PRE"}

FORM = {
    "slcTaxa": "PRE",
    "Data1": "20251201",
    "Data": "01/12/2025",
    "convertexls1": "",
    "nomexls": "",
    "lQtdTabelas": "",
    "IDIOMA": "1",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www2.bmf.com.br",
    "Referer": (
        "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/"
        "lum-taxas-referenciais-bmf-ptBR.asp?Data=01/12/2025&Data1=20251204&slcTaxa=PRE"
    ),
}

def cell_text(tag) -> str:
    return tag.get_text(" ", strip=True).replace("\xa0", " ")

def extract_table_matrix(table):
    """
    Returns a list[list[str]] for all rows in document order,
    expanding rowspan/colspan so the output is a rectangular-ish grid.
    Handles malformed HTML where <td>/<th> tags are not wrapped in <tr> tags.
    """
    grid = []
    rowspans = {}  # col_index -> [text, remaining_rows]

    # First, process proper <tr> tags
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue

        row = []
        col = 0

        def fill_active_rowspans_until_free():
            nonlocal col
            while col in rowspans:
                text, remaining = rowspans[col]
                row.append(text)
                remaining -= 1
                if remaining <= 0:
                    del rowspans[col]
                else:
                    rowspans[col] = [text, remaining]
                col += 1

        fill_active_rowspans_until_free()

        for c in cells:
            fill_active_rowspans_until_free()

            text = cell_text(c)
            rowspan = int(c.get("rowspan", 1) or 1)
            colspan = int(c.get("colspan", 1) or 1)

            for i in range(colspan):
                row.append(text)
                if rowspan > 1:
                    rowspans[col + i] = [text, rowspan - 1]
            col += colspan

        grid.append(row)

    # Handle malformed HTML: find loose <td>/<th> tags not inside <tr>
    # Separate them by type to handle headers vs data
    loose_th = []
    loose_td = []
    for elem in table.descendants:
        # Skip if it's inside a <tr>
        if elem.name == "th" and elem.find_parent("tr") is None:
            loose_th.append(elem)
        elif elem.name == "td" and elem.find_parent("tr") is None:
            loose_td.append(elem)
    
    # Determine column count from existing rows
    if grid:
        num_cols = len(grid[0])
    else:
        num_cols = 3  # default
    
    # Add loose <th> tags as additional header row(s)
    if loose_th:
        for i in range(0, len(loose_th), num_cols):
            row = []
            for j in range(num_cols):
                if i + j < len(loose_th):
                    row.append(cell_text(loose_th[i + j]))
                else:
                    row.append("")
            grid.append(row)
    
    # Add loose <td> tags as data rows
    if loose_td:
        for i in range(0, len(loose_td), num_cols):
            row = []
            for j in range(num_cols):
                if i + j < len(loose_td):
                    row.append(cell_text(loose_td[i + j]))
                else:
                    row.append("")
            grid.append(row)

    # pad to equal width
    width = max((len(r) for r in grid), default=0)
    for r in grid:
        r.extend([""] * (width - len(r)))
    return grid

def main() -> None:
    with requests.Session() as s:
        resp = s.post(URL, params=PARAMS, data=FORM, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding

    soup = BeautifulSoup(resp.text, "lxml")  # pip install lxml
    table = soup.select_one("table#tb_principal1")
    
    if not table:
        print("Table not found!", file=sys.stderr)
        sys.exit(1)
    
    # Extract table data as a matrix
    matrix = extract_table_matrix(table)
    
    if not matrix:
        print("No data extracted from table!", file=sys.stderr)
        sys.exit(1)
    
    # Calculate column widths
    col_widths = []
    num_cols = len(matrix[0]) if matrix else 0
    
    for col_idx in range(num_cols):
        max_width = max(len(row[col_idx]) if col_idx < len(row) else 0 for row in matrix)
        col_widths.append(max_width)
    
    # Count header rows (rows where most cells are not purely numeric data)
    num_header_rows = 0
    for row in matrix[:5]:  # Check first 5 rows max
        # If row has mostly non-numeric content, it's likely a header
        non_numeric = sum(1 for cell in row if not (
            cell.replace(".", "").replace(",", "").replace("-", "").replace("%", "").strip().isdigit()
        ))
        if non_numeric >= len(row) / 2:
            num_header_rows += 1
        else:
            break
    
    # Print the table with proper formatting
    for row_idx, row in enumerate(matrix):
        formatted_cells = []
        for col_idx, cell in enumerate(row):
            width = col_widths[col_idx]
            # Right-align numbers, left-align text
            if cell.replace(".", "").replace(",", "").replace("-", "").replace("%", "").strip().isdigit():
                formatted_cells.append(cell.rjust(width))
            else:
                formatted_cells.append(cell.ljust(width))
        
        print(" | ".join(formatted_cells))
        
        # Print separator after all header rows
        if row_idx == num_header_rows - 1 and num_header_rows > 0:
            separator = "-+-".join(["-" * w for w in col_widths])
            print(separator)

if __name__ == "__main__":
    main()
