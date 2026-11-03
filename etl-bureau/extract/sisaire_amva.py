"""PM2.5 medido en estaciones del AMVA (SISAIRE, datos.gov.co g4t8-zkc3).

El archivo nacional trae rezago: el corte verificado el 2026-11-02 llega
a 2025-12-31. Se guarda el promedio diario de las últimas observaciones,
no el modelado de Open-Meteo.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COLUMNS = ["fecha", "pm2_5", "n"]
URL = "https://www.datos.gov.co/resource/g4t8-zkc3.json"


def _vacio() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def agregar(filas) -> pd.DataFrame:
    df = pd.DataFrame(filas)
    if df.empty or "med_fecha_inicio" not in df.columns:
        return _vacio()
    df["fecha"] = df["med_fecha_inicio"].astype(str).str.slice(0, 10)
    df["pm2_5"] = pd.to_numeric(df["med_concentracion_estandar"], errors="coerce")
    df = df.dropna(subset=["fecha", "pm2_5"])
    if df.empty:
        return _vacio()
    g = df.groupby("fecha")["pm2_5"].agg(pm2_5="mean", n="count").reset_index()
    g["pm2_5"] = g["pm2_5"].round(2)
    return g.reindex(columns=COLUMNS).sort_values("fecha")


def run():
    df = _vacio()
    try:
        r = requests.get(
            URL,
            params={
                "$select": "med_fecha_inicio,med_concentracion_estandar",
                "$where": "nombre_fgda='AMVA' AND msfl_code='PM2.5'",
                "$order": "med_fecha_inicio DESC",
                "$limit": "5000",
            },
            headers=UA,
            timeout=90,
        )
        r.raise_for_status()
        df = agregar(r.json())
        print(f"[extract] sisaire_amva: {len(df)} días")
    except Exception as e:
        print(f"[extract][WARN] sisaire_amva: {e}")
    try:
        return [save_or_carry(df, "sisaire_amva", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] sisaire_amva save: {e}")
        return []


if __name__ == "__main__":
    run()
