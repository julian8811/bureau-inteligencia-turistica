"""IPC nacional, serie de empalme (DANE).

El anexo de índices publicado como xlsx es el total nacional, no el de
Medellín ni el de alojamiento. Esos cortes vienen en un .xls que este
pipeline no parsea. Se guarda el índice nacional de los últimos años
como contexto de precios, con esa limitación en el nombre del archivo.
"""

from datetime import date

import pandas as pd
import requests

from .base import UA, save_or_carry

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
ABREV = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
COLUMNS = ["anio", "mes", "indice"]


def candidatos(n: int = 6) -> list[str]:
    y, m = date.today().year, date.today().month
    urls = []
    for _ in range(n):
        mes = ABREV[m - 1]
        urls.append(
            f"https://www.dane.gov.co/files/operaciones/IPC/{mes}{y}/anex-IPC-Indices-{mes}{y}.xlsx"
        )
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return urls


def parse_indices(blob: bytes) -> pd.DataFrame:
    from io import BytesIO
    import openpyxl
    book = openpyxl.load_workbook(BytesIO(blob), read_only=True, data_only=True)
    ws = book.active
    rows = list(ws.iter_rows(values_only=True))
    book.close()
    header = next((i for i, row in enumerate(rows) if row and str(row[0]).strip().lower() == "mes"), None)
    if header is None:
        return pd.DataFrame(columns=COLUMNS)
    years = []
    for col, cell in enumerate(rows[header]):
        if col == 0 or cell is None:
            continue
        try:
            year = int(str(cell).strip())
        except ValueError:
            continue
        if year >= date.today().year - 2:
            years.append((col, year))
    recs = []
    for row in rows[header + 1:]:
        if not row or row[0] is None:
            continue
        mes = MESES.get(str(row[0]).strip().lower())
        if not mes:
            continue
        for col, year in years:
            if col >= len(row) or row[col] in (None, ""):
                continue
            try:
                recs.append({"anio": year, "mes": mes, "indice": round(float(row[col]), 2)})
            except (TypeError, ValueError):
                continue
    df = pd.DataFrame(recs, columns=COLUMNS)
    if not df.empty:
        df = df.sort_values(["anio", "mes"])
    return df


def run():
    df = pd.DataFrame(columns=COLUMNS)
    for url in candidatos():
        try:
            r = requests.get(url, headers=UA, timeout=60)
            if r.status_code != 200 or len(r.content) < 1000:
                continue
            df = parse_indices(r.content)
            print(f"[extract] dane_ipc: {len(df)} filas <- {url}")
            break
        except Exception as e:
            print(f"[extract][WARN] dane_ipc {url}: {e}")
    if df.empty:
        print("[extract][SKIP] dane_ipc: ningún anexo vivo")
    try:
        return [save_or_carry(df, "dane_ipc", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] dane_ipc save: {e}")
        return []


if __name__ == "__main__":
    run()
