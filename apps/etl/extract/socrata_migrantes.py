"""Socrata datos.gov.co c4mm-qn8q MIGRANTES A COLOMBIA.

Sin key. Paginacion $limit/$offset via base.paginate_socrata.
Guarda data/raw/<hoy>/migrantes_co.csv. Sin datos -> save_or_carry, jamas levanta.
"""
from datetime import date

import pandas as pd

from .base import paginate_socrata, save_or_carry

DATASET = "c4mm-qn8q"
OUT_NAME = "migrantes_co"
COLUMNS = ["nacionalidad", "total", "fecha_consulta"]


def parse_migrantes(payload: list | dict, hoy: str | None = None) -> pd.DataFrame:
    """Lista Socrata (o dict envuelto) -> DataFrame con fecha_consulta."""
    hoy = hoy or date.today().isoformat()
    if isinstance(payload, dict):
        for key in ("data", "results", "rows"):
            val = payload.get(key)
            if isinstance(val, list):
                payload = val
                break
        else:
            payload = [payload] if payload else []
    rows = [r for r in (payload or []) if isinstance(r, dict)]
    df = pd.DataFrame(rows)
    if df.empty:
        if rows:
            print(f"[socrata][SKIP] {DATASET} devuelve filas vacías (columnas no públicas) -> carry; entradas ya cubiertas por 96sh-4v8d")
        return pd.DataFrame({c: [] for c in COLUMNS})
    df = df.dropna(axis=1, how="all")
    if len(df.columns) == 0:
        print(f"[socrata][SKIP] {DATASET} sin columnas útiles (no públicas) -> carry; entradas ya cubiertas por 96sh-4v8d")
        return pd.DataFrame({c: [] for c in COLUMNS})
    df.columns = [str(c).strip().lower() for c in df.columns]
    df["fecha_consulta"] = hoy
    return df


def run() -> bool:
    try:
        raw = paginate_socrata(DATASET, {})
        df = parse_migrantes(raw.to_dict(orient="records") if not raw.empty else [])
        save_or_carry(df, OUT_NAME, COLUMNS)
        if df.empty:
            print(f"[socrata][SKIP] {DATASET} sin datos -> carry")
            return False
        print(f"[socrata] {OUT_NAME} OK ({len(df)} filas)")
        return True
    except Exception as e:
        print(f"[socrata][SKIP] {OUT_NAME}: {e}")
        try:
            save_or_carry(pd.DataFrame(), OUT_NAME, COLUMNS)
        except Exception as e2:
            print(f"[socrata][WARN] carry {OUT_NAME} fallido: {e2}")
        return False


if __name__ == "__main__":
    run()
