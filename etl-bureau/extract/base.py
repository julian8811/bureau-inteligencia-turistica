"""Extractores Tier-1: solo fuentes abiertas. Cada uno guarda data/raw/<fecha>/<fuente>.csv y nunca tumba el daily."""
from pathlib import Path
from datetime import date
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

def out_dir() -> Path:
    d = RAW / date.today().isoformat()
    d.mkdir(parents=True, exist_ok=True)
    return d

def save(df: pd.DataFrame, name: str) -> Path:
    p = out_dir() / f"{name}.csv"
    df.to_csv(p, index=False)
    print(f"[extract] {name}: {len(df)} filas -> {p}")
    return p
