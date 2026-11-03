"""Anexo mensual de la Encuesta Mensual de Alojamiento (DANE).

URL predecible: anex-EMA-{mes}{año}.xlsx. Prueba el mes en curso hacia
atrás. Guarda el xlsx y una fila con la URL que respondió. El parseo del
índice de Antioquia lo hace preparar_fuentes.py en tableros-bureau.
"""

from datetime import date

import pandas as pd
import requests

from .base import UA, out_dir, save_or_carry

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
COLUMNS = ["url", "bytes", "hojas"]


def candidatos(n: int = 8) -> list[str]:
    y, m = date.today().year, date.today().month
    urls = []
    for _ in range(n):
        urls.append(
            f"https://www.dane.gov.co/files/operaciones/EMA/anex-EMA-{MESES[m - 1]}{y}.xlsx"
        )
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return urls


def run():
    df = pd.DataFrame(columns=COLUMNS)
    for url in candidatos():
        try:
            r = requests.get(url, headers=UA, timeout=90)
            if r.status_code != 200 or len(r.content) < 50000:
                continue
            raw = out_dir() / "dane_ema.xlsx"
            raw.write_bytes(r.content)
            hojas = ""
            try:
                import openpyxl
                book = openpyxl.load_workbook(raw, read_only=True)
                hojas = "|".join(book.sheetnames[:12])
                book.close()
            except Exception as e:
                print(f"[extract][WARN] dane_ema hojas: {e}")
            df = pd.DataFrame([{"url": url, "bytes": len(r.content), "hojas": hojas}])
            print(f"[extract] dane_ema OK <- {url}")
            break
        except Exception as e:
            print(f"[extract][WARN] dane_ema {url}: {e}")
    if df.empty:
        print("[extract][SKIP] dane_ema: ningún anexo vivo")
    try:
        return [save_or_carry(df, "dane_ema", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] dane_ema save: {e}")
        return []


if __name__ == "__main__":
    run()
