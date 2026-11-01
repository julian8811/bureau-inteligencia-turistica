"""Compat: ahora el cableado real vive en socrata_co.py (datasets probados 27-oct-2026).
Este módulo queda como alias para no romper imports viejos."""
from .socrata_co import run  # noqa: F401
