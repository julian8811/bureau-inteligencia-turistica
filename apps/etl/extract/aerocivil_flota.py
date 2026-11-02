"""Aerocivil flota y operaciones: conectividad aerea (vacacional/MICE).

Datasets Socrata verificados 28-oct-2026 (catalogo verificado):
- djjf-g4q4 trafico por equipo (flota: que aviones mueven pasajeros/carga)
- w9ei-uhm3 operaciones por ruta y aerolinea (frecuencias, sillas)
Via paginate_socrata, sin key: hasta 5000 filas recientes por dataset
($order ano-reciente DESC en servidor si el esquema lo permite, fallback
:id DESC; recorte al ano maximo en cliente si hay columna de ano).
Dos run_* individuales + agregador que une ambas patas con columna
dataset y guarda data/raw/<hoy>/aerocivil_flota.csv via save_or_carry.
Trazabilidad S3/S4: conectividad aerea (sillas y frecuencias que sostienen
temporada vacacional y sede MICE).
"""

import pandas as pd

from .base import paginate_socrata, save_or_carry

DATASET_EQUIPO = "djjf-g4q4"
DATASET_RUTA = "w9ei-uhm3"
PAGE_SIZE = 1000
MAX_PAGES = 5  # 5000 filas recientes por dataset


def _query_reciente(dataset: str) -> pd.DataFrame:
    """Un intento SIN $order (el que funciona; barrido 01-nov: w9ei-uhm3
    falla con $order y trae dato al reintentar sin order). Sin segundo
    intento redundante: el recorte al ano maximo se hace en cliente."""
    try:
        df = paginate_socrata(dataset, {}, page_size=PAGE_SIZE, max_pages=MAX_PAGES)
    except Exception as e:
        print(f"[extract][WARN] aerocivil_flota {dataset} sin order: {str(e)[:150]}")
        return pd.DataFrame()
    if df.empty:
        print(f"[extract][WARN] aerocivil_flota {dataset} sin order: vacio")
    return df


def _recortar_ano_maximo(df: pd.DataFrame) -> pd.DataFrame:
    """Si hay columna de ano, conserva solo el ano maximo (reciente)."""
    try:
        cols = {c.lower(): c for c in df.columns}
        ano = next(
            (
                cols[c]
                for c in cols
                if c in ("a_o", "ano", "anio", "vigencia", "año", "year")
                or ("a" in c and "o" in c and len(c) <= 4)
            ),
            None,
        )
        if ano:
            anos = pd.to_numeric(df[ano], errors="coerce")  # type: ignore[arg-type]
            anos = pd.Series(anos)  # type: ignore[assignment]
            if bool(anos.notna().any()):  # type: ignore[attr-defined]
                df = df[anos == anos.max()]  # type: ignore[assignment]
    except Exception as e:
        print(f"[extract][WARN] aerocivil_flota recorte ano: {str(e)[:150]}")
    return df


def run_equipo() -> pd.DataFrame:
    """Individual: trafico por equipo djjf-g4q4 (nunca levanta)."""
    try:
        df = _query_reciente(DATASET_EQUIPO)
        print(f"[extract] aerocivil_flota equipo: {len(df)} filas {DATASET_EQUIPO}")
        if not df.empty:
            df = _recortar_ano_maximo(df)
            df["dataset"] = "trafico_equipo"
        return df
    except Exception as e:
        print(f"[extract][WARN] aerocivil_flota equipo: {str(e)[:150]}")
        return pd.DataFrame()


def run_ruta() -> pd.DataFrame:
    """Individual: operaciones por ruta y aerolinea w9ei-uhm3 (nunca levanta)."""
    try:
        df = _query_reciente(DATASET_RUTA)
        print(f"[extract] aerocivil_flota ruta: {len(df)} filas {DATASET_RUTA}")
        if not df.empty:
            df = _recortar_ano_maximo(df)
            df["dataset"] = "operaciones_ruta"
        return df
    except Exception as e:
        print(f"[extract][WARN] aerocivil_flota ruta: {str(e)[:150]}")
        return pd.DataFrame()


def run():
    """Agregador: equipo+ruta -> data/raw/<hoy>/aerocivil_flota.csv."""
    try:
        frames = [f for f in (run_equipo(), run_ruta()) if not f.empty]
        df = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
        print(f"[extract] aerocivil_flota: {len(df)} filas combinadas")
        return save_or_carry(df, "aerocivil_flota")
    except Exception as e:
        print(f"[extract][WARN] aerocivil_flota agregador: {str(e)[:150]}")
        return save_or_carry(pd.DataFrame(), "aerocivil_flota")


if __name__ == "__main__":
    run()
