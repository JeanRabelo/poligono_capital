#!/usr/bin/env python3
import sys
import requests
from bs4 import BeautifulSoup

URL = "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-taxas-referenciais-bmf-ptBR.asp"
DATA, DATA1, TAXA = "01/12/2025", "20251201", "PRE"

FORM = {
    "slcTaxa": TAXA, "Data1": DATA1, "Data": DATA,
    "convertexls1": "", "nomexls": "", "lQtdTabelas": "", "IDIOMA": "1",
}
PARAMS = {"Data": DATA, "Data1": DATA1, "slcTaxa": TAXA}
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": URL}

def txt(tag): return tag.get_text(" ", strip=True).replace("\xa0", " ")

def table_matrix(table, default_cols=3):
    grid, span = [], {}

    def fill(row, col):
        while col in span:
            t, n = span[col]
            row.append(t)
            n -= 1
            span[col] = (t, n) if n else span.pop(col)
            col += 1
        return col

    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells: 
            continue
        row, col = [], 0
        for c in cells:
            col = fill(row, col)
            t = txt(c)
            rs = int(c.get("rowspan", 1) or 1)
            cs = int(c.get("colspan", 1) or 1)
            for i in range(cs):
                row.append(t)
                if rs > 1:
                    span[col + i] = (t, rs - 1)
            col += cs
        grid.append(row)

    ncols = len(grid[0]) if grid else default_cols
    loose = [c for c in table.find_all(["th", "td"]) if c.find_parent("tr") is None]
    for i in range(0, len(loose), ncols):
        row = [txt(c) for c in loose[i:i + ncols]]
        row += [""] * (ncols - len(row))
        grid.append(row)

    w = max((len(r) for r in grid), default=0)
    for r in grid:
        r += [""] * (w - len(r))
    return grid

def main():
    r = requests.post(URL, params=PARAMS, data=FORM, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding

    soup = BeautifulSoup(r.text, "lxml")
    table = soup.select_one("#tb_principal1")
    if not table:
        print("table not found", file=sys.stderr)
        return 1

    for row in table_matrix(table):
        print("\t".join(row))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
