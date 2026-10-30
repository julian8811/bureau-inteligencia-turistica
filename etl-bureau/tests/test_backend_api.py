"""API lectura del backend. TDD: RED primero."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_URL = "host=/var/run/postgresql port=5433 dbname=bureau_test user=julian connect_timeout=10"


def _client(monkeypatch):
    from backend import writer
    monkeypatch.setenv("BACKEND_DATABASE_URL", TEST_URL)
    for k in ("GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    assert writer.run()["status"] == "ok"
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


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
