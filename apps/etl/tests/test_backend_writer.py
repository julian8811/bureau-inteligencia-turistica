"""Writer post-embudo LLM -> Postgres. TDD: RED primero."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_URL = "host=/var/run/postgresql port=5433 dbname=bureau_test user=julian connect_timeout=10"

ENV_KEYS = ("BACKEND_DATABASE_URL", "GITHUB_TOKEN", "GH_TOKEN")


def _scrub_env(monkeypatch):
    for k in ENV_KEYS:
        monkeypatch.delenv(k, raising=False)


def test_skip_sin_url(monkeypatch):
    from backend import writer
    _scrub_env(monkeypatch)
    res = writer.run()
    assert res["status"] == "skip"


def test_write_idempotente(monkeypatch):
    from backend import writer
    import psycopg
    _scrub_env(monkeypatch)
    monkeypatch.setenv("BACKEND_DATABASE_URL", TEST_URL)
    with psycopg.connect(TEST_URL) as con:
        with con.cursor() as cur:
            cur.execute("DELETE FROM marca_llm")
            cur.execute("DELETE FROM clasificacion_llm")
    r1 = writer.run()
    assert r1["status"] == "ok"
    assert r1["marca"] >= 1
    assert r1["clasificacion"] >= 1
    r2 = writer.run()
    assert r2 == r1, "re-correr el mismo día no duplica ni cambia conteos"
    with psycopg.connect(TEST_URL) as con:
        dias = con.execute("SELECT COUNT(DISTINCT dia) FROM marca_llm").fetchone()[0]
        assert dias == 1
        n = con.execute("SELECT COUNT(*) FROM clasificacion_llm").fetchone()[0]
        assert n == r1["clasificacion"]
