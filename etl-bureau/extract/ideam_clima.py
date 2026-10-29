"""Clima Medellín (IDEAM vía Socrata datos.gov.co) para MICE + vacacional.
- 57sv-p2fu observaciones IDEAM y terceros (temperatura/lluvia, municipio=Medellín con tilde).
- hp9r-jxuu catálogo de estaciones (dónde se mide).
- s54a-sgyg precipitación (lluvia, clave vacacional/eventos).
Límites pequeños + carry-forward si hoy falla. Nunca tumba el daily.
"""
from pathlib import Path

import pandas as pd

from .base import paginate_socrata, save_or_carry

OBS = "57sv-p2fu"
ESTACIONES = "hp9r-jxuu"
LLUVIA = "s54a-sgyg"
MUNI = "Medellín"


def _q(dataset: str, order: str | None = None) -> pd.DataFrame:
    try:
        params = {"municipio": MUNI}
        if order:
            params["$order"] = order
        return paginate_socrata(dataset, params, page_size=1500, max_pages=2)
    except Exception as e:
        print(f"[ideam_clima][WARN] {dataset}: {str(e)[:150]}")
        return pd.DataFrame()


def run_observaciones() -> Path:
    try:
        df = _q(OBS, "fechaobservacion DESC")
    except Exception as e:
        print(f"[ideam_clima][WARN] observaciones: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "ideam_observaciones_med")


def run_estaciones() -> Path:
    try:
        df = _q(ESTACIONES)
    except Exception as e:
        print(f"[ideam_clima][WARN] estaciones: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "ideam_estaciones_med")


def run_lluvia() -> Path:
    try:
        df = _q(LLUVIA, "fechaobservacion DESC")
    except Exception as e:
        print(f"[ideam_clima][WARN] lluvia: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "ideam_lluvia_med")


def run() -> list[Path]:
    return [run_observaciones(), run_estaciones(), run_lluvia()]


if __name__ == "__main__":
    run()
