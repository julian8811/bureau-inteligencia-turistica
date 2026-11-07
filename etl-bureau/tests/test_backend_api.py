"""API lectura del backend. TDD: RED primero."""
import sys
from pathlib import Path

import psycopg
import pyotp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_URL = "host=/var/run/postgresql port=5433 dbname=bureau_test user=julian connect_timeout=10"
TEST_SECRET = "secreto-tests-backend"


def _client(monkeypatch):
    from api.main import app
    from api.security import new_csrf_token, reset_attempts
    from backend import access, auth, writer
    from fastapi.testclient import TestClient
    monkeypatch.setenv("BACKEND_DATABASE_URL", TEST_URL)
    monkeypatch.setenv("AUTH_SESSION_SECRET", TEST_SECRET)
    for k in ("GITHUB_TOKEN", "GH_TOKEN", "SMTP_HOST"):
        monkeypatch.delenv(k, raising=False)
    reset_attempts()
    assert writer.run()["status"] == "ok"
    with psycopg.connect(TEST_URL, autocommit=True) as con:
        auth.ensure_auth_schema(con)
        access.ensure_access_schema(con)
        with con.cursor() as cur:
            cur.execute("DELETE FROM approval_outbox")
            cur.execute("DELETE FROM access_requests")
            cur.execute("DELETE FROM sessions")
            cur.execute("DELETE FROM login_audit")
            cur.execute("DELETE FROM app_users")
        tok = access.request_access(con, "Test", "test@colmayor.edu.co",
                                    "ColMayor", "tests", "interno")
        access.approve_request(con, tok, "admin@colmayor.edu.co")
        tsec = auth.new_totp_secret()
        access.activate_user(con, "test@colmayor.edu.co", "Password-tests-2026", tsec)
    c = TestClient(app)
    r = c.post("/auth/login", data={"email": "test@colmayor.edu.co",
                                    "password": "Password-tests-2026",
                                    "totp": pyotp.TOTP(tsec).now(),
                                    "csrf_token": new_csrf_token(TEST_SECRET)})
    assert r.status_code == 200, r.text
    return c


def test_health(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["db"] == "ok"


def test_marca(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/marca")
    assert r.status_code == 200
    body = r.json()
    assert body["dia"] != ""
    assert len(body["rows"]) >= 1
    assert "categoria" in body["rows"][0]


def test_informes_vacio_ok(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/informes", params={"corte": "1900-01-01"})
    assert r.status_code == 200
    assert r.json()["rows"] == []
