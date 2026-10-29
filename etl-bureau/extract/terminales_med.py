"""Terminales de Transporte de Medellin: movilidad terrestre (vacacional/MICE).

Datasets Socrata verificados 28-oct-2026 (probe directo con datos):
- aesn-q83n salidas y llegadas de vehiculos y pasajeros (Norte/Sur)
- a45t-7a3r espejo del mismo reporte (fallback si el primario falla)
Via paginate_socrata, sin key: hasta 5000 filas recientes por dataset
($order :id DESC, recorte al anio maximo en cliente si hay columna).
Dos run_* individuales + agregador que une ambas patas con columna
dataset y guarda data/raw/<hoy>/terminales_med.csv via save_or_carry.
Trazabilidad: buses intermunicipales que sostienen temporada vacacional
y llegada de asistentes MICE por tierra.
"""

import pandas as pd

from .base import paginate_socrata, save_or_carry

DATASETS = ["aesn-q83n", "a45t-7a3r"]
PAGE_SIZE = 1000
MAX_PAGES = 5  # 5000 filas recientes por dataset


def _reciente(dataset: str) -> pd.DataFrame:
    """Filas recientes (fallback :id si el esquema no tiene anio)."""
    try:
        df = paginate_socrata(
            dataset, {"$order": ":id DESC"},
            page_size=PAGE_SIZE, max_pages=MAX_PAGES,
        )
    except Exception as e:
        print(f"[extract][WARN] terminales_med {dataset}: {str(e)[:150]}")
        return pd.DataFrame()
    if df.empty:
        print(f"[extract][WARN] terminales_med {dataset}: vacio")
    return df


def run_dataset(dataset: str) -> pd.DataFrame:
    """run() individual: un dataset de terminales con columna trazadora."""
    df = _reciente(dataset)
    if not df.empty:
        df = df.copy()
        df["dataset"] = dataset
    return df


def run() -> list:
    """Agregador: aesn-q83n primario + a45t-7a3r fallback, guarda uno solo."""
    frames = []
    for ds in DATASETS:
        df = run_dataset(ds)
        if not df.empty:
            frames.append(df)
    out: pd.DataFrame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not out.empty and "dataset" in out.columns:
        cols = [c for c in out.columns if c != "dataset"] + ["dataset"]
        out = pd.DataFrame(out[cols])
    p = save_or_carry(out, "terminales_med")
    return [p]


if __name__ == "__main__":
    run()
