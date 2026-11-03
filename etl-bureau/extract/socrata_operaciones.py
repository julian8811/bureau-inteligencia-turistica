"""Operaciones aéreas MDE/EOH (Aerocivil, datos.gov.co jh8x-n6h6).

El dataset nacional pasa de 100 mil filas por año. Aquí se pide solo
el agregado mensual de SKRG y SKMD desde 2024, que es el grano del
bloque de conectividad.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COLUMNS = ["anio", "mes", "totaloperaciones"]
URL = "https://www.datos.gov.co/resource/jh8x-n6h6.json"


def _vacio() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run():
    df = _vacio()
    try:
        r = requests.get(
            URL,
            params={
                "$select": "anio,mes,sum(totaloperaciones) as totaloperaciones",
                "$where": "aeropuerto_operacion in('SKRG','SKMD') AND anio>='2024'",
                "$group": "anio,mes",
                "$order": "anio,mes",
                "$limit": "80",
            },
            headers=UA,
            timeout=90,
        )
        r.raise_for_status()
        df = pd.DataFrame(r.json()).reindex(columns=COLUMNS)
        print(f"[extract] operaciones_aereas: {len(df)} meses")
    except Exception as e:
        print(f"[extract][WARN] operaciones_aereas: {e}")
    try:
        return [save_or_carry(df, "operaciones_aereas", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] operaciones_aereas save: {e}")
        return []


if __name__ == "__main__":
    run()
