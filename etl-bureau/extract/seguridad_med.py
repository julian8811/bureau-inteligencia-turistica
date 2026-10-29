"""Seguridad Medellín — hurtos y homicidios Policía Nacional (Socrata datos.gov.co).
Temática T3: MICE (seguridad de sedes/eventos) + marca (percepción de ciudad).
- HURTO PERSONAS 4rxi-8m8d, HOMICIDIO m8fd-ahd9 (municipio=MEDELLIN, sin tilde).
Límites pequeños (1000 filas x 3 págs) + carry-forward si hoy falla. Nunca tumba el daily.
"""
from pathlib import Path

import pandas as pd

from .base import paginate_socrata, save_or_carry

HURTOS = "4rxi-8m8d"
HOMICIDIOS = "m8fd-ahd9"


def _q(dataset: str, muni: str = "MEDELLIN") -> pd.DataFrame:
    try:
        return paginate_socrata(
            dataset,
            {"municipio": muni, "$order": "fecha_hecho DESC"},
            page_size=1000,
            max_pages=3,
        )
    except Exception as e:
        print(f"[seguridad_med][WARN] {dataset}: {str(e)[:150]}")
        return pd.DataFrame()


def run_hurtos() -> Path:
    try:
        df = _q(HURTOS)
    except Exception as e:
        print(f"[seguridad_med][WARN] hurtos: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "seguridad_hurtos_med")


def run_homicidios() -> Path:
    try:
        df = _q(HOMICIDIOS)
    except Exception as e:
        print(f"[seguridad_med][WARN] homicidios: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "seguridad_homicidios_med")


def run() -> list[Path]:
    return [run_hurtos(), run_homicidios()]


if __name__ == "__main__":
    run()
