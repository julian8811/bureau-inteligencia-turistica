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
EMISORES = ["US", "MX", "BR", "ES", "PA", "FR", "DO"]
COLUMNS = ["date", "localName", "name", "countryCode", "year"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run_year(year: int, country: str = "CO") -> pd.DataFrame:
    """Festivos públicos de un país y un año."""
    try:
        r = requests.get(
            f"https://date.nager.at/api/v3/publicholidays/{year}/{country}",
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
                    "countryCode": row.get("countryCode", country),
                    "year": year,
                }
            )
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        print(f"[extract] festivos {country} {year}: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] festivos {country} {year}: {e}")
        return _empty()


def _concat(paises: list[str]) -> pd.DataFrame:
    frames = []
    for country in paises:
        for year in YEARS:
            frame = run_year(year, country)
            if not frame.empty:
                frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else _empty()


def run():
    """Colombia en festivos_co.csv y los emisores en festivos_emisores.csv."""
    salidas = []
    try:
        df = _concat(["CO"])
    except Exception as e:
        print(f"[extract][WARN] festivos_co agregador: {e}")
        df = _empty()
    try:
        salidas.append(save_or_carry(df, "festivos_co", COLUMNS))
    except Exception as e:
        print(f"[extract][WARN] festivos_co save: {e}")
    try:
        emisores = _concat(EMISORES)
    except Exception as e:
        print(f"[extract][WARN] festivos_emisores agregador: {e}")
        emisores = _empty()
    try:
        salidas.append(save_or_carry(emisores, "festivos_emisores", COLUMNS))
    except Exception as e:
        print(f"[extract][WARN] festivos_emisores save: {e}")
    return salidas


if __name__ == "__main__":
    run()
