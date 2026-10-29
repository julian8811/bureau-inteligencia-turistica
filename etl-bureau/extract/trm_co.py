"""TRM proxy via open.er-api.com — USD base, tasa COP.

Tematica: MICE/vacacional — TRM COP/USD para derrama y pricing de eventos.
Endpoint free sin key: https://open.er-api.com/v6/latest/USD
(la guia decia /v1/, que hoy devuelve 404; /v6/ es la ruta free abierta
del mismo host y responde 200 con rates.COP).
Si falla -> carry-forward via save_or_carry, nunca tumba el daily.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COLUMNS = ["base", "date", "rate_cop"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run_rate() -> pd.DataFrame:
    """run() individual: tasa USD->COP del dia."""
    try:
        r = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        payload = r.json()
        cop = ((payload or {}).get("rates") or {}).get("COP")
        df = pd.DataFrame(
            [
                {
                    "base": payload.get("base_code", "USD"),
                    "date": payload.get("time_last_update_utc", ""),
                    "rate_cop": cop,
                }
            ]
        ).reindex(columns=COLUMNS)
        print(f"[extract] trm_co: {len(df)} filas (COP={cop})")
        return df
    except Exception as e:
        print(f"[extract][WARN] trm_co: {e}")
        return _empty()


def run():
    """run() agregador: guarda data/raw/<hoy>/trm_co.csv con carry-forward."""
    try:
        df = run_rate()
    except Exception as e:
        print(f"[extract][WARN] trm_co agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "trm_co", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] trm_co save: {e}")
        return []


if __name__ == "__main__":
    run()
