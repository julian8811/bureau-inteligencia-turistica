"""Movilidad Medellín para eventos MICE: Metro (único en el daily).
- Metro: MEData Alcaldía (CSV pasajeros movilizados mensual, verificado 28-oct-2026).
- Terminales: FUERA del daily desde 31-oct-2026 (S2/S3) — el extractor
  canónico de terminales es extract/terminales_med.py (alimenta pax_terminal_mes);
  run_terminales() queda solo como legado/manual y no lo llama run().
  No se borra historia en data/raw.
Límites pequeños + carry-forward si hoy falla. Nunca tumba el daily.
"""
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from .base import UA, paginate_socrata, save_or_carry

METRO_CSV = "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000197/pasajeros_movilizados_mensual_metro_de_medellin.csv"
TERMINALES = "eze3-t67n"


def run_metro_pasajeros() -> Path:
    df = pd.DataFrame()
    for url in (METRO_CSV, METRO_CSV.replace("https://", "http://")):
        try:
            r = requests.get(url, headers=UA, timeout=25)
            r.raise_for_status()
            if len(r.content) < 100:
                continue
            try:
                df = pd.read_csv(StringIO(r.text))
            except Exception:
                df = pd.read_csv(StringIO(r.text), sep=";", encoding="latin-1")
            if not df.empty:
                break
        except Exception as e:
            print(f"[metro_movilidad][WARN] metro {url[:60]}: {str(e)[:130]}")
    return save_or_carry(df, "movilidad_metro_med")


def run_terminales() -> Path:
    """Legado/manual: FUERA del daily (S2/S3 31-oct-2026). Ver terminales_med."""
    try:
        df = paginate_socrata(
            TERMINALES,
            {"$order": "fecha_programada DESC"},
            page_size=1500,
            max_pages=2,
        )
    except Exception as e:
        print(f"[metro_movilidad][WARN] terminales: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "movilidad_terminales_med")


def run() -> list[Path]:
    """Daily: solo Metro. Terminales va por terminales_med (pax_terminal_mes)."""
    return [run_metro_pasajeros()]


if __name__ == "__main__":
    run()
