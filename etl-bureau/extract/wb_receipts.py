"""World Bank ST.INT.RCPT + ST.INT.XPND — gasto/ingreso turismo internacional.

Tematica: gasto vacacional/MICE (derrama emisores + Colombia).
Evidencia 28-oct-2026: patron probado en un_wb_arrivals.py
https://api.worldbank.org/v2/country/COL;ESP;USA/indicator/ST.INT.ARVL?format=json&date=2019:2024
Si un indicador/pais falla -> SKIP honesto con carry-forward, nunca tumba el daily.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COUNTRIES = ["COL", "USA", "ESP", "MEX", "PAN", "WLD"]
# Spec: ST.INT.RCPT + ST.INT.XPND. La API v2 rechaza los codigos sin sufijo
# (error 120 "Invalid value"); se usan las variantes .CD (current US$),
# que son el mismo concepto documentado por el Banco Mundial.
INDICATORS = ["ST.INT.RCPT.CD", "ST.INT.XPND.CD"]
YEARS = "2019:2024"
COLUMNS = ["countryiso3code", "country", "year", "value", "indicator"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run_indicator(code: str, indicator: str) -> pd.DataFrame:
    """run() individual: un indicador de un pais via World Bank v2."""
    url = f"https://api.worldbank.org/v2/country/{code}/indicator/{indicator}"
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
                    "value": row.get("value"),
                    "indicator": indicator,
                }
            )
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        print(f"[extract] wb_receipts {code}/{indicator}: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] wb_receipts {code}/{indicator}: {e}")
        return _empty()


def run():
    """run() agregador: concatena paises x indicadores y guarda data/raw/<hoy>/wb_receipts.csv."""
    try:
        frames = [run_indicator(c, i) for c in COUNTRIES for i in INDICATORS]
        df = pd.concat(frames, ignore_index=True) if frames else _empty()
    except Exception as e:
        print(f"[extract][WARN] wb_receipts agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "wb_receipts", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] wb_receipts save: {e}")
        return []


if __name__ == "__main__":
    run()
