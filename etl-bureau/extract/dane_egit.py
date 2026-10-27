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
                # guarda el xlsx crudo + intenta leer primera hoja a csv
                raw = out_dir() / f"{name}.xlsx"
                raw.write_bytes(r.content)
                try:
                    df = pd.read_excel(BytesIO(r.content), sheet_name=0)
                    df["fuente_url"] = u
                    save(df, name)
                except Exception as e:
                    print(f"[dane][WARN] {name} xlsx guardado pero no parseado: {e}")
                print(f"[dane] {name} OK <- {u}")
                return True
        except Exception as e:
            print(f"[dane][WARN] {u}: {e}")
            continue
    print(f"[dane][SKIP] {name}: ningún anexo vivo en lookback")
    return False

def run():
    fetch_first(candidate_urls("EGIT"), "dane_egit")
    fetch_first(candidate_urls("ENH"), "dane_enh")

if __name__ == "__main__":
    run()
