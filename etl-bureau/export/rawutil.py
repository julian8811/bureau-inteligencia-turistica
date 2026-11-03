"""Directorio RAW más reciente. No falla si todavía no hay corridas."""
from pathlib import Path


def latest_raw(base: Path) -> Path | None:
    root = base / "data" / "raw"
    if not root.is_dir():
        return None
    cands = sorted(p for p in root.glob("20*") if p.is_dir())
    return cands[-1] if cands else None
