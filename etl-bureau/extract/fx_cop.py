"""FX COP via currency-api (fawazahmed0) — USD base, tasas COP/EUR/MXN/BRL.

Tematica: derrama y pricing — tasa COP para dashboard Bureau.
Frankfurter verificado hoy solo devuelve EUR (sin COP) -> no sirve.
Endpoint free sin key:
https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json
(verificado COP=3201 el 2026-11-01; payload trae `date` + `usd.cop/eur/mxn/brl`).
Si falla -> carry-forward via save_or_carry, nunca tumba el daily.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
COLUMNS = ["base", "date", "cop", "eur", "mxn", "brl"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def parse_rates(payload: dict) -> pd.DataFrame:
    """Parse payload currency-api -> 1 fila USD base con cop/eur/mxn/brl."""
    try:
        payload = payload or {}
        usd = payload.get("usd") or {}
        row = {
            "base": "USD",
            "date": payload.get("date", ""),
            "cop": usd.get("cop"),
            "eur": usd.get("eur"),
            "mxn": usd.get("mxn"),
            "brl": usd.get("brl"),
        }
        if row["cop"] is None and row["eur"] is None:
            return _empty()
        df = pd.DataFrame([row]).reindex(columns=COLUMNS)
        print(f"[extract] fx_cop parse: date={row['date']} COP={row['cop']}")
        return df
    except Exception as e:
        print(f"[extract][WARN] fx_cop parse: {e}")
        return _empty()


def run_rate() -> pd.DataFrame:
    """run() individual: tasas USD->COP/EUR/MXN/BRL del dia."""
    try:
        r = requests.get(URL, headers=UA, timeout=60)
        r.raise_for_status()
        df = parse_rates(r.json())
        if not df.empty:
            print(f"[extract] fx_cop: {len(df)} filas (COP={df.iloc[0]['cop']})")
        return df
    except Exception as e:
        print(f"[extract][WARN] fx_cop: {e}")
        return _empty()


def run():
    """run() agregador: guarda data/raw/<hoy>/fx_cop.csv con carry-forward."""
    try:
        df = run_rate()
    except Exception as e:
        print(f"[extract][WARN] fx_cop agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "fx_cop", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] fx_cop save: {e}")
        return []


if __name__ == "__main__":
    run()
