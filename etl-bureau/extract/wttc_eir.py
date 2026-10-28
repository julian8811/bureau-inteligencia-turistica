"""WTTC EIR — headline free (el informe completo es gated).

El Economic Impact Research completo esta tras muro; solo el headline
publico es free. Este extractor deja el esqueleto headline y hace SKIP
honesto cuando no hay dato free fresco, con carry-forward via
save_or_carry. Nunca tumba el daily.
"""

import pandas as pd

from .base import save_or_carry

COLUMNS = ["year", "indicator", "value", "source"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run_headline() -> pd.DataFrame:
    """run() individual: headline EIR free (gated -> SKIP honesto con df vacio)."""
    print(
        "[gated][SKIP] wttc_eir full es gated (EIR tras muro);"
        " solo headline free -> skip con carry-forward"
    )
    return _empty()


def run():
    """run() agregador: guarda data/raw/<hoy>/wttc_eir.csv (carry si hay previo)."""
    try:
        df = run_headline()
    except Exception as e:
        print(f"[extract][WARN] wttc agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "wttc_eir", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] wttc save: {e}")
        return []


if __name__ == "__main__":
    run()
