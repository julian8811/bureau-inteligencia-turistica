"""Conexion Postgres del backend. Sin URL -> None (SKIP honesto)."""
import os

URL_KEYS = ("BACKEND_DATABASE_URL", "DATABASE_URL")


def get_url() -> str:
    for k in URL_KEYS:
        v = os.environ.get(k, "").strip()
        if v:
            return v
    return ""


def connect():
    import psycopg
    # prepare_threshold=None: sin prepared statements nombrados (el pooler
    # Supavisor/pgbouncer en modo transacción los rompe entre conexiones).
    return psycopg.connect(get_url(), connect_timeout=10, prepare_threshold=None)
