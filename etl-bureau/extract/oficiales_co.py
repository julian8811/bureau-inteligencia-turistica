"""Fuentes oficiales Colombia: CITUR / Migración / Aerocivil.
Lee CSVs públicos (URLs configurables por env). Si cambian, deja stub vacío y avisa, no rompe."""
import os
import pandas as pd
from .base import save

SOURCES = {
    "citur": os.getenv("CITUR_CSV_URL", ""),
    "migracion": os.getenv("MIGRACION_CSV_URL", ""),
    "aerocivil": os.getenv("AEROCIVIL_CSV_URL", ""),
}

def run_one(name: str, url: str):
    try:
        if not url:
            print(f"[extract][SKIP] {name}: sin URL (configurar env). Stub vacío.")
            return save(pd.DataFrame([{"fuente": name, "nota": "configurar CSV_URL"}]), name)
        df = pd.read_csv(url)
        df["fuente"] = name
        return save(df, name)
    except Exception as e:
        print(f"[extract][WARN] {name} falló: {e}")
        return save(pd.DataFrame([{"fuente": name, "error": str(e)}]), name)

def run():
    return [run_one(k, v) for k, v in SOURCES.items()]

if __name__ == "__main__":
    run()
