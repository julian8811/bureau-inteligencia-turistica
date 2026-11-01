"""Festivos Colombia via Nager.at — temporada vacacional/MICE.

Tematica: vacacional/MICE — festivos definen puentes, temporada alta y
disponibilidad de venues/eventos en Medellin.
Endpoints free sin key:
  https://date.nager.at/api/v3/publicholidays/2026/CO
  https://date.nager.at/api/v3/publicholidays/2025/CO
Si un ano falla -> SKIP honesto de ese ano con carry-forward.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

YEARS = [2026, 2025]
COLUMNS = ["date", "localName", "name", "countryCode", "year"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run_year(year: int) -> pd.DataFrame:
    """run() individual: festivos de Colombia de un ano."""
    try:
        r = requests.get(
            f"https://date.nager.at/api/v3/publicholidays/{year}/CO",
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        recs = []
        for row in r.json() or []:
            recs.append(
                {
                    "date": row.get("date", ""),
                    "localName": row.get("localName", ""),
                    "name": row.get("name", ""),
                    "countryCode": row.get("countryCode", "CO"),
                    "year": year,
                }
            )
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        print(f"[extract] festivos_co {year}: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] festivos_co {year}: {e}")
        return _empty()


def run():
    """run() agregador: concatena anos y guarda data/raw/<hoy>/festivos_co.csv."""
    try:
        frames = [f for f in (run_year(y) for y in YEARS) if not f.empty]
        df = pd.concat(frames, ignore_index=True) if frames else _empty()
    except Exception as e:
        print(f"[extract][WARN] festivos_co agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "festivos_co", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] festivos_co save: {e}")
        return []


if __name__ == "__main__":
    run()
