"""Volumen de menciones de Medellín en el último corte de GDELT 2.0.

El DOC API responde 429 de forma persistente. En su lugar se baja el
GKG de los últimos 15 minutos (lastupdate.txt) y se cuentan las líneas
que mencionan Medellín. No hay espera de minutos: si falla, carry-forward.
"""

import io
import zipfile
from datetime import datetime, timedelta

import pandas as pd
import requests

from .base import save_or_carry

COLS = ["date", "value", "query"]
LAST = "https://data.gdeltproject.org/gdeltv2/lastupdate.txt"


def count_medellin(blob: bytes) -> int:
    n = 0
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as fh:
            for raw in fh:
                low = raw.lower()
                if b"medellin" in low or b"medell\xc3\xadn" in low:
                    n += 1
    return n


def _fecha(url: str) -> str:
    nombre = url.rsplit("/", 1)[-1]
    digitos = "".join(ch for ch in nombre if ch.isdigit())[:8]
    try:
        return datetime.strptime(digitos, "%Y%m%d").date().isoformat()
    except ValueError:
        return ""


def _cortes(url: str, n: int = 4) -> list[str]:
    nombre = url.rsplit("/", 1)[-1]
    sello = "".join(ch for ch in nombre if ch.isdigit())[:14]
    base = url.rsplit("/", 1)[0]
    inicio = datetime.strptime(sello, "%Y%m%d%H%M%S")
    return [
        f"{base}/{(inicio - timedelta(minutes=15 * i)).strftime('%Y%m%d%H%M%S')}.gkg.csv.zip"
        for i in range(n)
    ]


def run():
    df = pd.DataFrame(columns=COLS)
    try:
        meta = requests.get(LAST, timeout=30)
        meta.raise_for_status()
        url = ""
        for line in meta.text.splitlines():
            parts = line.split()
            if parts and parts[-1].endswith(".gkg.csv.zip"):
                url = parts[-1]
                break
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        if not url:
            raise RuntimeError("lastupdate sin GKG")
        total = 0
        for corte in _cortes(url):
            blob = requests.get(corte, timeout=90)
            if blob.status_code != 200:
                print(f"[gdelt][WARN] {corte.rsplit('/', 1)[-1]}: {blob.status_code}")
                continue
            total += count_medellin(blob.content)
        df = pd.DataFrame([{"date": _fecha(url), "value": total, "query": "medellin_gkg_1h"}])
        print(f"[extract] gdelt_marca: {total} menciones en la última hora ({_fecha(url)})")
    except Exception as e:
        print(f"[gdelt][WARN] {str(e)[:180]}")
    return save_or_carry(df, "gdelt_marca", columns=COLS)


if __name__ == "__main__":
    run()
