"""Extractores Tier-1: solo fuentes abiertas. Cada uno guarda data/raw/<fecha>/<fuente>.csv y nunca tumba el daily."""
from pathlib import Path
from datetime import date
import shutil
import requests
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) bureau-etl/1.0"}

def out_dir() -> Path:
    d = RAW / date.today().isoformat()
    d.mkdir(parents=True, exist_ok=True)
    return d

def latest_file(name: str) -> Path | None:
    cands = sorted(RAW.glob(f"*/{name}.csv"))
    return cands[-1] if cands else None

def save(df: pd.DataFrame, name: str, columns: list[str] | None = None) -> Path:
    if df.empty and columns:
        df = pd.DataFrame(columns=columns)
    p = out_dir() / f"{name}.csv"
    df.to_csv(p, index=False)
    print(f"[extract] {name}: {len(df)} filas -> {p}")
    return p

def save_or_carry(df: pd.DataFrame, name: str, columns: list[str] | None = None) -> Path:
    """Si hoy falla (vacío) y hay dato previo de OTRO día, arrastra el último bueno (forward-fill)."""
    if df.empty or (columns and list(df.columns) == columns and df.empty):
        cands = sorted(p for p in RAW.glob(f"*/{name}.csv") if p.parent.name != date.today().isoformat())
        if cands:
            try:
                old = pd.read_csv(cands[-1])
                if not old.empty:
                    p = save(old, name)
                    print(f"[extract][CARRY] {name}: hoy vacío, se arrastra {cands[-1].parent.name} ({len(old)} filas)")
                    return p
            except Exception as e:
                print(f"[extract][WARN] carry {name}: {e}")
    return save(df, name, columns)

def paginate_socrata(dataset: str, params: dict, page_size: int = 50000, max_pages: int = 20) -> pd.DataFrame:
    """Paginación $limit/$offset hasta agotar (corta si una página viene incompleta)."""
    frames, offset = [], 0
    for _ in range(max_pages):
        q = dict(params, **{"$limit": str(page_size), "$offset": str(offset)})
        try:
            r = requests.get(f"https://www.datos.gov.co/resource/{dataset}.json", params=q, timeout=60)
            r.raise_for_status()
            batch = pd.DataFrame(r.json())
        except Exception as e:
            print(f"[socrata][WARN] {dataset} offset={offset}: {e}")
            break
        if batch.empty:
            break
        frames.append(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    print(f"[socrata] {dataset}: {len(out)} filas en {len(frames)} páginas")
    return out
