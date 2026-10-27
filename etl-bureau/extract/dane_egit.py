"""DANE EGIT + ENH: anexos Excel con URL predecible por trimestre.
Patrón: https://www.dane.gov.co/files/operaciones/EGIT/anex-EGIT-IItrim2026.xlsx
Se prueba el trimestre actual hacia atrás hasta encontrar uno vivo. Trimestral, gratis.
ENH (hoteles): mismo esquema con ruta /ENH/.
"""
import requests
from io import BytesIO
from datetime import date
import pandas as pd
from .base import save, out_dir

TRIM = {1: "Itrim", 2: "IItrim", 3: "IIItrim", 4: "IVtrim"}

def candidate_urls(kind: str = "EGIT", lookback_q: int = 6) -> list[str]:
    urls = []
    y, m = date.today().year, date.today().month
    q = (m - 1) // 3 + 1
    for _ in range(lookback_q):
        t = TRIM[q]
        if kind == "EGIT":
            urls.append(f"https://www.dane.gov.co/files/operaciones/EGIT/anex-EGIT-{t}{y}.xlsx")
        else:
            urls.append(f"https://www.dane.gov.co/files/operaciones/ENH/anex-ENH-{t}{y}.xlsx")
        q -= 1
        if q == 0:
            q, y = 4, y - 1
    return urls

def fetch_first(urls: list[str], name: str):
    for u in urls:
        try:
            r = requests.get(u, timeout=40)
            if r.status_code == 200 and len(r.content) > 50000:
                # guarda el xlsx crudo + parsea hojas clave a CSVs largos
                raw = out_dir() / f"{name}.xlsx"
                raw.write_bytes(r.content)
                parse_egit_sheets(BytesIO(r.content), u)
                print(f"[dane] {name} OK <- {u}")
                return True
        except Exception as e:
            print(f"[dane][WARN] {u}: {e}")
            continue
    print(f"[dane][SKIP] {name}: ningún anexo vivo en lookback")
    return False

# Hojas clave EGIT: (hoja, nombre_csv). Estructura: fila "Concepto" = header, trimestres cada 3 cols.
EGIT_SHEETS = [
    ("8. Gasto promedio día turismo", "dane_egit_gasto_dia"),
    ("2. Turismo interno", "dane_egit_turismo_interno"),
    ("5. Turismo tipo de alojamiento", "dane_egit_alojamiento"),
    ("6.Turismo promedio pernoctación", "dane_egit_pernoctacion"),
]

def parse_egit_sheets(buf: BytesIO, url: str):
    from .base import save
    x = pd.ExcelFile(buf)
    for sheet, csv_name in EGIT_SHEETS:
        try:
            if sheet not in x.sheet_names:
                print(f"[dane][WARN] hoja faltante: {sheet}")
                continue
            raw = pd.read_excel(x, sheet_name=sheet, header=None)
            # fila header = la que contiene "Concepto" en col 0
            hdr = raw[raw[0].astype(str).str.contains("Concepto", na=False)].index
            if len(hdr) == 0:
                continue
            hi = hdr[0]
            ncols = raw.shape[1]
            # columna de valor = header con nombre de trimestre (rompe el patrón cada-3 por la col anual 2025†)
            import re
            tri = re.compile(r"^\s*(I{1,3}V?\s*-\s*\d|2025)")
            pos = [p for p in range(1, ncols) if tri.match(str(raw.iat[hi, p]))]
            trim_names = [str(raw.iat[hi, p]).strip() for p in pos]
            body = raw.iloc[hi + 1 :, [0] + pos].reset_index(drop=True)
            body.columns = ["concepto"] + trim_names
            body = body[body["concepto"].notna() & (body["concepto"].astype(str).str.strip() != "")]
            long = body.melt(id_vars="concepto", var_name="trimestre", value_name="valor")
            # limpia columnas fantasma (header NaN al final) y sub-headers internos
            long = long[long["trimestre"].notna() & (long["trimestre"].astype(str).str.strip().str.lower() != "nan") & (long["trimestre"].astype(str).str.strip() != "")]
            long = long[long["concepto"].astype(str).str.strip().str.lower() != "concepto"]
            long["fuente_url"] = url
            long["hoja"] = sheet
            save(long, csv_name)
        except Exception as e:
            print(f"[dane][WARN] parse {sheet}: {e}")

def run():
    fetch_first(candidate_urls("EGIT"), "dane_egit")
    fetch_first(candidate_urls("ENH"), "dane_enh")

if __name__ == "__main__":
    run()
