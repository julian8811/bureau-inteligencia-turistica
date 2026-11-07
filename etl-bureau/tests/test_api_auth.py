"""Blindaje total: endpoints protegidos, rate-limit, headers, CSRF. TDD RED (T4: S2,S7)."""
import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_URL = "host=/var/run/postgresql port=5433 dbname=bureau_test user=julian connect_timeout=10"


def _secret():
    return os.environ.get("AUTH_SESSION_SECRET", "secreto-solo-tests-t4")


def _client(monkeypatch):
    from api.main import app
    from api.security import reset_attempts
    from backend import access, auth
    monkeypatch.setenv("BACKEND_DATABASE_URL", TEST_URL)
    monkeypatch.setenv("AUTH_SESSION_SECRET", _secret())
    for k in ("GITHUB_TOKEN", "GH_TOKEN", "SMTP_HOST"):
        monkeypatch.delenv(k, raising=False)
    reset_attempts()
    with psycopg.connect(TEST_URL, autocommit=True) as con:
        auth.ensure_auth_schema(con)
        access.ensure_access_schema(con)
        with con.cursor() as cur:
            cur.execute("DELETE FROM approval_outbox")
            cur.execute("DELETE FROM access_requests")
            cur.execute("DELETE FROM sessions")
            cur.execute("DELETE FROM login_audit")
            cur.execute("DELETE FROM app_users")
    from fastapi.testclient import TestClient
    return TestClient(app)


def _alta(con_email="ana@colmayor.edu.co", tipo="interno"):
    from backend import access, auth
    with psycopg.connect(TEST_URL, autocommit=True) as con:
        tok = access.request_access(con, "Ana", con_email, "ColMayor", "ver", tipo)
        access.approve_request(con, tok, "admin@colmayor.edu.co")
        secret = auth.new_totp_secret()
        access.activate_user(con, con_email, "Password-larga-2026", secret)
        return secret


def _csrf():
    from api.security import new_csrf_token
    return new_csrf_token(_secret())


def _login(c, email, pw, totp):
    return c.post("/auth/login", data={"email": email, "password": pw,
                                       "totp": totp, "csrf_token": _csrf()})


def test_protegido_sin_sesion_401(monkeypatch):
    c = _client(monkeypatch)
    assert c.get("/marca").status_code == 401


def test_login_ok_da_cookie_y_accede(monkeypatch):
    import pyotp
    c = _client(monkeypatch)
    secret = _alta()
    r = _login(c, "ana@colmayor.edu.co", "Password-larga-2026", pyotp.TOTP(secret).now())
    assert r.status_code == 200, r.text
    assert "bureau_session" in r.cookies
    assert c.get("/marca").status_code == 200
    assert c.post("/auth/logout").status_code == 200
    assert c.get("/marca").status_code == 401


def test_login_pendiente_403(monkeypatch):
    from backend import access
    c = _client(monkeypatch)
    with psycopg.connect(TEST_URL, autocommit=True) as con:
        access.request_access(con, "Gil", "gil@colmayor.edu.co", "ColMayor", "ver", "interno")
    r = _login(c, "gil@colmayor.edu.co", "Password-larga-2026", "123456")
    assert r.status_code == 403


def test_rate_limit_bloquea(monkeypatch):
    c = _client(monkeypatch)
    _alta()
    for _ in range(5):
        assert _login(c, "ana@colmayor.edu.co", "Wrong-password-000", "000000").status_code in (401, 429)
    r = _login(c, "ana@colmayor.edu.co", "Wrong-password-000", "000000")
    assert r.status_code == 429


def test_headers_seguridad(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/marca")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "frame-ancestors" in r.headers.get("content-security-policy", "")


def test_login_sin_csrf_403(monkeypatch):
    import pyotp
    c = _client(monkeypatch)
    secret = _alta()
    r = c.post("/auth/login", data={"email": "ana@colmayor.edu.co",
                                    "password": "Password-larga-2026",
                                    "totp": pyotp.TOTP(secret).now()})
    assert r.status_code == 403


def test_login_devuelve_token_en_body(monkeypatch):
    import pyotp
    c = _client(monkeypatch)
    secret = _alta()
    r = _login(c, "ana@colmayor.edu.co", "Password-larga-2026", pyotp.TOTP(secret).now())
    assert r.status_code == 200
    assert r.json().get("token"), "el front Vercel necesita el token en el body"


def test_yo_con_header_ok(monkeypatch):
    import pyotp
    c = _client(monkeypatch)
    secret = _alta()
    r = _login(c, "ana@colmayor.edu.co", "Password-larga-2026", pyotp.TOTP(secret).now())
    token = r.json()["token"]
    c.cookies.clear()
    r2 = c.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200, r2.text
    assert r2.json().get("ok") is True


def test_yo_sin_nada_401(monkeypatch):
    c = _client(monkeypatch)
    assert c.get("/auth/yo").status_code == 401


def test_cors_permite_vercel(monkeypatch):
    c = _client(monkeypatch)
    r = c.options("/auth/login", headers={
        "Origin": "https://tableros-bureau.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert r.headers.get("access-control-allow-origin") == "https://tableros-bureau.vercel.app"
