"""Sesiones con cookie, CSRF con HMAC, rate-limit en memoria y headers (T4: S2,S7).

Nota: el rate-limit es por proceso (vale con un worker uvicorn; con N
workers usar Redis). Sin AUTH_SESSION_SECRET no hay sesiones válidas.
"""
import hashlib
import hmac
import os
import time
from datetime import datetime, timezone

from fastapi import HTTPException, Request

COOKIE = "bureau_session"
MAX_FAILS = 5
LOCK_SECONDS = 15 * 60
CSRF_TTL_SECONDS = 30 * 60
SESSION_DAYS = 7

_attempts: dict = {}


def session_secret() -> str:
    return os.environ.get("AUTH_SESSION_SECRET", "")


def _client_key(email: str, ip: str) -> str:
    return f"{email}|{ip}"


def login_allowed(email: str, ip: str) -> bool:
    _fails, until = _attempts.get(_client_key(email, ip), (0, 0.0))
    return time.time() >= until


def register_failure(email: str, ip: str) -> None:
    fails, until = _attempts.get(_client_key(email, ip), (0, 0.0))
    fails += 1
    if fails >= MAX_FAILS:
        until = time.time() + LOCK_SECONDS
    _attempts[_client_key(email, ip)] = [fails, until]


def register_success(email: str, ip: str) -> None:
    _attempts.pop(_client_key(email, ip), None)


def reset_attempts() -> None:
    _attempts.clear()


def new_csrf_token(secret: str = "") -> str:
    key = secret or session_secret()
    ts = str(int(time.time()))
    sig = hmac.new(key.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def check_csrf_token(token: str, secret: str = "") -> bool:
    key = secret or session_secret()
    if not key:
        return False
    try:
        ts, sig = str(token).rsplit(".", 1)
        if abs(time.time() - int(ts)) > CSRF_TTL_SECONDS:
            return False
        want = hmac.new(key.encode(), ts.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(want, sig)
    except Exception:
        return False


def new_session_token(user_id: str) -> str:
    from backend import auth as _auth
    return _auth.new_session_token(user_id, session_secret())


async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


def current_user(request: Request) -> str:
    from backend import auth as _auth
    from backend import db
    token = request.cookies.get(COOKIE, "")
    if not token:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    user_id = _auth.check_session_token(token, session_secret()) if token else None
    if not user_id:
        raise HTTPException(401, "sin sesión")
    if not db.get_url():
        raise HTTPException(503, "sin BACKEND_DATABASE_URL")
    try:
        con = db.connect()
    except Exception as e:
        raise HTTPException(503, f"sin conexion ({e})") from e
    try:
        with con.cursor() as cur:
            digest = hashlib.sha256(token.encode()).hexdigest()
            row = cur.execute("SELECT user_id, expira FROM sessions"
                              " WHERE token_hash = %s", (digest,)).fetchone()
            if not row:
                raise HTTPException(401, "sesión inválida")
            stored_id, expira = row
            exp = expira if expira.tzinfo else expira.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                raise HTTPException(401, "sesión vencida")
            urow = cur.execute("SELECT estado FROM app_users WHERE id = %s",
                               (stored_id,)).fetchone()
            if not urow or urow[0] != "activo":
                raise HTTPException(403, "sin acceso")
            return stored_id
    finally:
        con.close()
