"""Open-Meteo Ensemble Medellin — spread diario P10-P90 lluvia para riesgo outdoor MICE.

Tematica: clima-riesgo — dispersion del ensemble decide plan B en eventos.
Endpoint free sin key (exige models=icon_seamless; sin models da 400):
https://ensemble-api.open-meteo.com/v1/ensemble
  ?latitude=6.25&longitude=-75.57
  &daily=temperature_2m_max,precipitation_sum
  &timezone=America/Bogota&models=icon_seamless
Parse daily.time + members temperature_2m_max_memberXX y
precipitation_sum_memberXX -> media, p10, p90 por dia.
Si falla -> carry-forward via save_or_carry, nunca tumba el daily.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
LAT, LON = 6.25, -75.57
COLUMNS = ["date", "tmax_mean", "prec_mean", "prec_p10", "prec_p90", "n_members"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def parse_ensemble(payload: dict) -> pd.DataFrame:
    """Parse payload ensemble -> 1 fila por dia con media/p10/p90."""
    try:
        daily = (payload or {}).get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            return _empty()
        tmax_keys = sorted(k for k in daily if k.startswith("temperature_2m_max_member"))
        prec_keys = sorted(k for k in daily if k.startswith("precipitation_sum_member"))
        if not tmax_keys and not prec_keys:
            return _empty()
        recs = []
        for i, d in enumerate(dates):
            tvals = [daily[k][i] for k in tmax_keys
                     if isinstance(daily.get(k), list) and i < len(daily[k])
                     and daily[k][i] is not None]
            pvals = [daily[k][i] for k in prec_keys
                     if isinstance(daily.get(k), list) and i < len(daily[k])
                     and daily[k][i] is not None]
            n = max(len(tvals), len(pvals))
            if n == 0:
                continue
            ts = pd.Series(tvals, dtype=float) if tvals else pd.Series([], dtype=float)
            ps = pd.Series(pvals, dtype=float) if pvals else pd.Series([], dtype=float)
            recs.append({
                "date": d,
                "tmax_mean": float(ts.mean()) if not ts.empty else None,
                "prec_mean": float(ps.mean()) if not ps.empty else None,
                "prec_p10": float(ps.quantile(0.1)) if not ps.empty else None,
                "prec_p90": float(ps.quantile(0.9)) if not ps.empty else None,
                "n_members": n,
            })
        if not recs:
            return _empty()
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        members = max(len(tmax_keys), len(prec_keys))
        print(f"[extract] openmeteo_ensemble parse: {len(df)} dias, {members} members")
        return df
    except Exception as e:
        print(f"[extract][WARN] openmeteo_ensemble parse: {e}")
        return _empty()


def run_ensemble() -> pd.DataFrame:
    """run() individual: spread ensemble Medellin."""
    try:
        r = requests.get(
            URL,
            params={
                "latitude": LAT,
                "longitude": LON,
                "daily": "temperature_2m_max,precipitation_sum",
                "timezone": "America/Bogota",
                "models": "icon_seamless",
            },
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        df = parse_ensemble(r.json())
        print(f"[extract] openmeteo_ensemble: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] openmeteo_ensemble: {e}")
        return _empty()


def run():
    """run() agregador: guarda data/raw/<hoy>/openmeteo_ensemble.csv con carry-forward."""
    try:
        df = run_ensemble()
    except Exception as e:
        print(f"[extract][WARN] openmeteo_ensemble agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "openmeteo_ensemble", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] openmeteo_ensemble save: {e}")
        return []


if __name__ == "__main__":
    run()
