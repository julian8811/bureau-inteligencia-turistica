"""Aire Medellin: calidad del aire para eventos y temporada (vacacional/MICE).

Endpoint Open-Meteo air-quality API verificado 200 el 28-oct-2026:
  https://air-quality-api.open-meteo.com/v1/air-quality
  ?latitude=6.25&longitude=-75.57&hourly=pm2_5&forecast_days=3
Free sin key, patron openmeteo_med.py (requests + timeout 30s, parse
defensivo, save_or_carry). Guarda data/raw/<hoy>/aire_med.csv.
Trazabilidad S3/S4: eventos/vacacional (PM2.5 condiciona actividades al
aire libre, agenda cultural y comunicacion de destino).
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

LAT, LON = 6.25, -75.57
URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
COLUMNS = ["datetime", "pm2_5"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _to_frame(payload: dict) -> pd.DataFrame:
    try:
        hourly = (payload or {}).get("hourly") or {}
        times = hourly.get("time") or []
        pm = hourly.get("pm2_5") or []
        recs = [
            {
                "datetime": t,
                "pm2_5": pm[i] if i < len(pm) else None,
            }
            for i, t in enumerate(times)
        ]
        df = pd.DataFrame(recs)
        return df.reindex(columns=COLUMNS) if not df.empty else _empty()
    except Exception as e:
        print(f"[extract][WARN] aire_med parse: {str(e)[:150]}")
        return _empty()


def run_aq() -> pd.DataFrame:
    """Individual: PM2.5 horario Medellin, 3 dias forecast (nunca levanta)."""
    try:
        r = requests.get(
            URL,
            params={
                "latitude": LAT,
                "longitude": LON,
                "hourly": "pm2_5",
                "forecast_days": 3,
                "timezone": "America/Bogota",
            },
            headers=UA,
            timeout=30,
        )
        r.raise_for_status()
        df = _to_frame(r.json())
        print(f"[extract] aire_med: {len(df)} filas horarias")
        return df
    except Exception as e:
        print(f"[extract][WARN] aire_med: {str(e)[:150]}")
        return _empty()


def run():
    """Agregador: PM2.5 -> data/raw/<hoy>/aire_med.csv (carry si hoy falla)."""
    try:
        df = run_aq()
        return save_or_carry(df, "aire_med", COLUMNS)
    except Exception as e:
        print(f"[extract][WARN] aire_med agregador: {str(e)[:150]}")
        return save_or_carry(pd.DataFrame(), "aire_med")


if __name__ == "__main__":
    run()
