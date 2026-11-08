"""QR de activación. TDD: RED primero (qr server-side, sin terceros)."""
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_URL = "host=/var/run/postgresql port=5433 dbname=bureau_test user=julian connect_timeout=10"


def _client(monkeypatch):
    from api.main import app
    from backend import access, auth
    monkeypatch.setenv("BACKEND_DATABASE_URL", TEST_URL)
    monkeypatch.setenv("AUTH_SESSION_SECRET", "secreto-qr-tests")
    for k in ("GITHUB_TOKEN", "GH_TOKEN", "SMTP_HOST"):
        monkeypatch.delenv(k, raising=False)
    with psycopg.connect(TEST_URL, autocommit=True) as con:
        auth.ensure_auth_schema(con)
        access.ensure_access_schema(con)
        with con.cursor() as cur:
            cur.execute("DELETE FROM approval_outbox")
            cur.execute("DELETE FROM access_requests")
            cur.execute("DELETE FROM sessions")
            cur.execute("DELETE FROM login_audit")
            cur.execute("DELETE FROM app_users")
        tok = access.request_access(con, "QR", "qr@colmayor.edu.co", "ColMayor", "ver", "interno")
        access.approve_request(con, tok, "admin@colmayor.edu.co")
    from fastapi.testclient import TestClient
    return TestClient(app)


def _csrf(c):
    return c.get("/auth/csrf").json()["csrf_token"]


def test_activar_con_qr_devuelve_png(monkeypatch):
    pytest.importorskip("qrcode")
    c = _client(monkeypatch)
    r = c.post("/auth/activar-mfa", data={"email": "qr@colmayor.edu.co",
                                          "password": "Password-qr-2026!",
                                          "csrf_token": _csrf(c), "qr": "1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("qr_png", "").startswith("data:image/png;base64,")
    import base64
    raw = base64.b64decode(body["qr_png"].split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "debe ser un PNG real"
