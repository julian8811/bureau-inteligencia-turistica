"""World Bank ST.INT.DPRT + ST.INT.XPND — salidas y gasto de los emisores.

Emisores que viajan/vuelven (vacacional/MICE): COL USA ESP MEX PAN + WLD.
Evidencia 28-oct-2026 (parent): WB API v2 200 OK.
Patron: un_wb_arrivals.py (run_country + agregador + save_or_carry).
Nunca tumba el daily: todo try/except, timeout <=30s, sin nuevas dependencias.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COUNTRIES = ["COL", "USA", "ESP", "MEX", "PAN", "WLD"]
INDICATORS = ["ST.INT.DPRT", "ST.INT.XPND.CD"]
YEARS = "2019:2024"
COLUMNS = ["countryiso3code", "country", "year", "value", "indicator"]
TIMEOUT = 30


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run_indicator(country: str, indicator: str) -> pd.DataFrame:
    """run() individual: un indicador de un pais via World Bank v2."""
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
    try:
        r = requests.get(
            url,
            params={"format": "json", "date": YEARS, "per_page": 50},
            headers=UA,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        payload = r.json()
        rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        recs = []
        for row in rows or []:
            recs.append(
                {
                    "countryiso3code": country,
                    "country": (row.get("country") or {}).get("value", ""),
                    "year": row.get("date", ""),
                    "value": row.get("value"),
                    "indicator": indicator,
                }
            )
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        print(f"[extract] wb_departures {country} {indicator}: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] wb_departures {country} {indicator}: {e}")
        return _empty()


def run():
    """run() agregador: concatena paises x indicadores y guarda data/raw/<hoy>/wb_departures.csv."""
    try:
        frames = [run_indicator(c, i) for c in COUNTRIES for i in INDICATORS]
        df = pd.concat(frames, ignore_index=True) if frames else _empty()
    except Exception as e:
        print(f"[extract][WARN] wb_departures agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "wb_departures", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] wb_departures save: {e}")
        return []


if __name__ == "__main__":
    run()
