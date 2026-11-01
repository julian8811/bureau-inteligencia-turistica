"""Open-Meteo Medellin — clima forecast + archive (lat 6.25, lon -75.57).

Tematica: MICE/vacacional — clima decide sede de eventos y temporada.
Endpoints free sin key:
  forecast: https://api.open-meteo.com/v1/forecast
  archive:  https://archive-api.open-meteo.com/v1/archive
Si uno falla -> SKIP honesto de esa pata con carry-forward, nunca inventar datos.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

LAT, LON = 6.25, -75.57
COLUMNS = ["date", "kind", "temp_max", "temp_min", "precipitation"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _to_frame(payload: dict, kind: str) -> pd.DataFrame:
    try:
        daily = (payload or {}).get("daily") or {}
        dates = daily.get("time") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        prec = daily.get("precipitation_sum") or []
        recs = []
        for i, d in enumerate(dates):
            recs.append(
                {
                    "date": d,
                    "kind": kind,
                    "temp_max": tmax[i] if i < len(tmax) else None,
                    "temp_min": tmin[i] if i < len(tmin) else None,
                    "precipitation": prec[i] if i < len(prec) else None,
                }
            )
        return pd.DataFrame(recs).reindex(columns=COLUMNS)
    except Exception as e:
        print(f"[extract][WARN] openmeteo parse {kind}: {e}")
        return _empty()


def run_forecast() -> pd.DataFrame:
    """run() individual: pronostico 7 dias Medellin."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LAT,
                "longitude": LON,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "America/Bogota",
            },
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        df = _to_frame(r.json(), "forecast")
        print(f"[extract] openmeteo forecast: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] openmeteo forecast: {e}")
        return _empty()


def run_archive() -> pd.DataFrame:
    """run() individual: ultimos 30 dias observados Medellin."""
    try:
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": LAT,
                "longitude": LON,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "America/Bogota",
                "past_days": 30,
            },
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        df = _to_frame(r.json(), "archive")
        print(f"[extract] openmeteo archive: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] openmeteo archive: {e}")
        return _empty()


def run():
    """run() agregador: concatena forecast+archive y guarda data/raw/<hoy>/openmeteo_med.csv."""
    try:
        frames = [f for f in (run_forecast(), run_archive()) if not f.empty]
        df = pd.concat(frames, ignore_index=True) if frames else _empty()
    except Exception as e:
        print(f"[extract][WARN] openmeteo agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "openmeteo_med", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] openmeteo save: {e}")
        return []


if __name__ == "__main__":
    run()
