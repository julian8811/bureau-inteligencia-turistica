"""Auth core login alta seguridad (T1: S3,S7). Sin deps nuevas: argon2 + pyotp + stdlib."""
import hashlib
import hmac
import secrets
import time
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

SCHEMA = Path(__file__).resolve().parent / "schema_auth.sql"
_PH = PasswordHasher()

MIN_PASS_LEN = 12


def password_ok(pw: str) -> bool:
    return isinstance(pw, str) and len(pw) >= MIN_PASS_LEN


def hash_password(pw: str) -> str:
    if not password_ok(pw):
        raise ValueError("password debe tener al menos 12 caracteres")
    return _PH.hash(pw)


def verify_password(stored: str, pw: str) -> bool:
    try:
        return _PH.verify(stored, pw)
    except (VerifyMismatchError, Exception):
        return False


def new_totp_secret() -> str:
    import pyotp

    return pyotp.random_base32()


def totp_uri(secret: str, email: str, issuer: str = "Bureau-ETL") -> str:
    import pyotp

    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    import pyotp

    try:
        return bool(pyotp.TOTP(secret).verify(str(code), valid_window=1))
    except Exception:
        return False


def can_login(estado: str) -> bool:
    """S3: solo 'activo' entra; pendiente/rechazado/expirado siempre False."""
    return estado == "activo"


def new_session_token(user_id: str, secret: str) -> str:
    payload = f"{user_id}:{int(time.time())}:{secrets.token_urlsafe(16)}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def check_session_token(token: str, secret: str):
    try:
        payload, sig = token.rsplit(".", 1)
        want = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, sig):
            return None
        return payload.split(":", 1)[0]
    except Exception:
        return None


def ensure_auth_schema(con) -> None:
    # DDL como literales: sin input de usuario ni interpolación posible.
    # Mantener sincronizado con backend/schema_auth.sql (artefacto para ops/psql).
    with con.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS app_users ("
            "id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, "
            "nombre TEXT NOT NULL DEFAULT '', "
            "tipo TEXT NOT NULL DEFAULT 'invitado' "
            "CHECK (tipo IN ('interno', 'invitado', 'admin')), "
            "estado TEXT NOT NULL DEFAULT 'pendiente' "
            "CHECK (estado IN ('pendiente', 'activo', 'rechazado', 'expirado')), "
            "pass_hash TEXT NOT NULL DEFAULT '', "
            "totp_secret TEXT NOT NULL DEFAULT '', "
            "expira_el DATE NULL, creado TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS access_requests ("
            "id SERIAL PRIMARY KEY, email TEXT NOT NULL, "
            "nombre TEXT NOT NULL DEFAULT '', institucion TEXT NOT NULL DEFAULT '', "
            "motivo TEXT NOT NULL DEFAULT '', "
            "tipo TEXT NOT NULL DEFAULT 'invitado' "
            "CHECK (tipo IN ('interno', 'invitado')), "
            "estado TEXT NOT NULL DEFAULT 'pendiente' "
            "CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')), "
            "token_aprobacion TEXT UNIQUE NOT NULL, "
            "creado TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "token_hash TEXT PRIMARY KEY, "
            "user_id TEXT NOT NULL REFERENCES app_users(id) ON DELETE CASCADE, "
            "expira TIMESTAMPTZ NOT NULL, creado TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS login_audit ("
            "id SERIAL PRIMARY KEY, email TEXT NOT NULL DEFAULT '', "
            "evento TEXT NOT NULL, ok BOOLEAN NOT NULL, ip TEXT NOT NULL DEFAULT '', "
            "creado TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
