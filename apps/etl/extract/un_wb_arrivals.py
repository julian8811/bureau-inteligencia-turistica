"""World Bank ST.INT.ARVL — llegadas de turistas internacionales (proxy UN, no UN directo).

La ONU (UN Tourism) no expone API free directa; se usa el indicador
ST.INT.ARVL del World Bank como proxy documentado (mismo dato base UN).
Evidencia 28-oct-2026: 200 OK en
https://api.worldbank.org/v2/country/COL;ESP;USA/indicator/ST.INT.ARVL?format=json&date=2019:2024&per_page=50
Patron base: save/save_or_carry, out_dir, UA. Nunca tumba el daily.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COUNTRIES = ["COL", "ESP", "USA", "FRA", "MEX"]
INDICATOR = "ST.INT.ARVL"
YEARS = "2019:2024"
COLUMNS = ["countryiso3code", "country", "year", "arrivals", "indicator"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run_country(code: str) -> pd.DataFrame:
    """run() individual: llegadas de un pais via World Bank v2."""
    url = f"https://api.worldbank.org/v2/country/{code}/indicator/{INDICATOR}"
    try:
        r = requests.get(
            url,
            params={"format": "json", "date": YEARS, "per_page": 50},
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        payload = r.json()
        rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        recs = []
        for row in rows or []:
            recs.append(
                {
                    "countryiso3code": code,
                    "country": (row.get("country") or {}).get("value", ""),
                    "year": row.get("date", ""),
                    "arrivals": row.get("value"),
                    "indicator": INDICATOR,
                }
            )
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        print(f"[extract] wb_arrivals {code}: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] wb_arrivals {code}: {e}")
        return _empty()


def run():
    """run() agregador: concatena paises y guarda data/raw/<hoy>/wb_arrivals.csv."""
    try:
        frames = [run_country(c) for c in COUNTRIES]
        df = pd.concat(frames, ignore_index=True) if frames else _empty()
    except Exception as e:
        print(f"[extract][WARN] wb_arrivals agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "wb_arrivals", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] wb_arrivals save: {e}")
        return []


if __name__ == "__main__":
    run()
