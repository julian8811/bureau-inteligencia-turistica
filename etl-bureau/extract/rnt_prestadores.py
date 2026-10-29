"""RNT prestadores: oferta formal MinCIT en Medellín (vacacional/MICE).
Dataset nacional thwd-ivmp "Registro Nacional de Turismo - RNT" vía
paginate_socrata, sin key: hasta 5000 filas recientes ($order :id DESC,
páginas de 1000) con filtro municipio=Medellín en cliente (esquema:
municipio, estado_rnt, categoria, sub_categoria...). Verificado 29-oct-2026.
Guarda data/raw/<hoy>/rnt_prestadores.csv vía save_or_carry.
Trazabilidad S4: vacacional (oferta formal: alojamiento, agencias, operadores).
"""

import pandas as pd

from .base import paginate_socrata, save_or_carry

DATASET = "thwd-ivmp"
PAGE_SIZE = 1000
MAX_PAGES = 5  # 5000 filas del nacional, filtro Medellín en cliente


def _filtrar_medellin(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra municipio Medellín en cliente (case-insensitive)."""
    try:
        cols = {c.lower(): c for c in df.columns}
        muni = next(
            (
                cols[c]
                for c in cols
                if "municipio" in c or "ciudad" in c or "destino" in c
            ),
            None,
        )
        if muni:
            df = df[df[muni].astype(str).str.contains("medell", case=False, na=False)]  # type: ignore[assignment]
    except Exception as e:
        print(f"[extract][WARN] rnt_prestadores filtro: {str(e)[:150]}")
    return df


def run_rnt(dataset: str | None = None) -> pd.DataFrame:
    """Individual: prestadores RNT de Medellín (vacío si falla, nunca levanta)."""
    try:
        ds = dataset or DATASET
        df = paginate_socrata(
            ds, {"$order": ":id DESC"}, page_size=PAGE_SIZE, max_pages=MAX_PAGES
        )
        print(f"[extract] rnt_prestadores: {len(df)} filas nacionales {ds}")
        if not df.empty:
            df = _filtrar_medellin(df)
        return df
    except Exception as e:
        print(f"[extract][WARN] rnt_prestadores {dataset}: {str(e)[:150]}")
        return pd.DataFrame()


def run():
    """Agregador: RNT Medellín -> data/raw/<hoy>/rnt_prestadores.csv (carry si hoy falla)."""
    try:
        df = run_rnt()
        print(f"[extract] rnt_prestadores: {len(df)} prestadores Medellín")
        return save_or_carry(df, "rnt_prestadores")
    except Exception as e:
        print(f"[extract][WARN] rnt_prestadores agregador: {str(e)[:150]}")
        return save_or_carry(pd.DataFrame(), "rnt_prestadores")


if __name__ == "__main__":
    run()
