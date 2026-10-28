"""Gated Brand24 (trial CSV o API key, nunca scraping con login).

Busca data/raw/manual/brand24*.csv|xlsx o BRAND24_KEY.
Sin nada -> SKIP. Con archivo -> lo normaliza a data/raw/<hoy>/brand24.csv
columnas esperadas: fecha,titulo,url,sentimiento,alcance.
"""
import os
import shutil
from datetime import date
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def run():
    hoy = date.today().isoformat()
    outdir = RAW / hoy
    outdir.mkdir(parents=True, exist_ok=True)
    manual = []
    if (RAW / "manual").exists():
        manual = sorted((RAW / "manual").glob("brand24*"))
    if not manual and not os.getenv("BRAND24_KEY"):
        print("[gated][SKIP] brand24 sin CSV trial ni BRAND24_KEY -> skip")
        return None
    if manual:
        src = manual[0]
        dst = outdir / "brand24.csv"
        try:
            if src.suffix == ".csv":
                shutil.copy(src, dst)
            else:
                import pandas as pd
                pd.read_excel(src).to_csv(dst, index=False)
            print(f"[gated] brand24 {src.name} -> {dst}")
            return dst
        except Exception as e:
            print(f"[gated][WARN] brand24 {src.name}: {e}")
            return None
    print("[gated][SKIP] BRAND24_KEY presente pero sin conector HTTP cableado -> pedir CSV trial")
    return None


if __name__ == "__main__":
    run()
