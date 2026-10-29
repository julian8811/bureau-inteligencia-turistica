"""RNT Antioquia (sin Medellin): oferta formal regional MinCIT (vacacional/MICE).

Datasets Socrata verificados 28-oct-2026 (Vista RNT Antioquia, catalogo
verificado): mmsn-v5r4 (primario) o u69p-k7vd (fallback). Via
paginate_socrata, sin key: hasta 5000 filas recientes ($order :id DESC,
paginas de 1000) con filtro departamento=Antioquia / excluir Medellin en
cliente (rnt_prestadores ya cubre Medellin). Guarda
data/raw/<hoy>/rnt_antioquia.csv via save_or_carry.
Trazabilidad S3/S4: vacacional/MICE (oferta formal regional fuera de la
capital: alojamiento rural, operadores, agencias Oriente/Suroeste).
"""

import pandas as pd

from .base import paginate_socrata, save_or_carry

DATASETS = ["mmsn-v5r4", "u69p-k7vd"]
PAGE_SIZE = 1000
MAX_PAGES = 5  # 5000 filas recientes, filtro Antioquia/Medellin en cliente


def _col(df: pd.DataFrame, *candidatas: str) -> str | None:
    cols = {c.lower(): c for c in df.columns}
    for cand in candidatas:
        for low, orig in cols.items():
            if cand in low:
                return orig
    return None


def _filtrar_antioquia_sin_medellin(df: pd.DataFrame) -> pd.DataFrame:
    """Departamento Antioquia en cliente; excluye Medellin (ya cubierta)."""
    try:
        depto = _col(df, "departamento", "dpto", "depto")
        if depto:
            mask = df[depto].astype(str).str.contains("antioquia", case=False, na=False)
            df = df[mask]  # type: ignore[assignment]
        muni = _col(df, "municipio", "ciudad", "destino")
        if muni:
            mask = df[muni].astype(str).str.contains("medell", case=False, na=False)
            df = df[~mask]  # type: ignore[assignment]
    except Exception as e:
        print(f"[extract][WARN] rnt_antioquia filtro: {str(e)[:150]}")
    return df


def run_rnt(dataset: str | None = None) -> pd.DataFrame:
    """Individual: prestadores RNT de Antioquia sin Medellin (nunca levanta)."""
    try:
        candidatos = [dataset] if dataset else list(DATASETS)
        for ds in candidatos:
            try:
                df = paginate_socrata(
                    ds, {"$order": ":id DESC"}, page_size=PAGE_SIZE, max_pages=MAX_PAGES
                )
            except Exception as e:
                print(f"[extract][WARN] rnt_antioquia {ds}: {str(e)[:150]}")
                continue
            if df.empty:
                print(f"[extract][WARN] rnt_antioquia {ds}: vacio, pruebo siguiente")
                continue
            print(f"[extract] rnt_antioquia: {len(df)} filas {ds}")
            return _filtrar_antioquia_sin_medellin(df)
        return pd.DataFrame()
    except Exception as e:
        print(f"[extract][WARN] rnt_antioquia {dataset}: {str(e)[:150]}")
        return pd.DataFrame()


def run():
    """Agregador: RNT Antioquia sin Medellin -> data/raw/<hoy>/rnt_antioquia.csv."""
    try:
        df = run_rnt()
        print(f"[extract] rnt_antioquia: {len(df)} prestadores Antioquia sin Medellin")
        return save_or_carry(df, "rnt_antioquia")
    except Exception as e:
        print(f"[extract][WARN] rnt_antioquia agregador: {str(e)[:150]}")
        return save_or_carry(pd.DataFrame(), "rnt_antioquia")


if __name__ == "__main__":
    run()
