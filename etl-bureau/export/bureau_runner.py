"""Corre los exportadores bureau_* y no reemplaza un JSON bueno por un skip.

SIT solo corre si hay PDFs en /tmp/sit: sin ellos el builder publica
mercados vacíos y borraría los perfiles ya citados.
"""
import json
from pathlib import Path

from export import (
    bureau_calendario,
    bureau_clima,
    bureau_conectividad,
    bureau_oferta,
    bureau_owid,
    bureau_seguridad,
    bureau_sit,
)

SIT_DIR = Path("/tmp/sit")
MODULOS = (
    bureau_oferta,
    bureau_seguridad,
    bureau_clima,
    bureau_conectividad,
    bureau_calendario,
    bureau_owid,
)


def _estado(blob: bytes | None) -> str | None:
    if not blob:
        return None
    try:
        return json.loads(blob.decode("utf-8")).get("estado")
    except Exception:
        return None


def _correr(mod) -> None:
    out = mod.OUT
    antes = out.read_bytes() if out.exists() else None
    try:
        mod.main()
    except Exception as exc:
        print(f"[export][WARN] {mod.__name__}: {exc}")
        if antes is not None:
            out.write_bytes(antes)
        return
    if _estado(out.read_bytes() if out.exists() else None) == "skip" and _estado(antes) == "ok":
        out.write_bytes(antes)
        print(f"[export] {mod.__name__}: skip, se conserva el JSON anterior")


def run() -> None:
    for mod in MODULOS:
        _correr(mod)
    if fitz_listos():
        _correr(bureau_sit)
    else:
        print("[export] bureau_sit: sin PDFs en /tmp/sit, se conserva el JSON anterior")


def fitz_listos() -> bool:
    try:
        return SIT_DIR.is_dir() and any(SIT_DIR.glob("*.pdf"))
    except Exception:
        return False
