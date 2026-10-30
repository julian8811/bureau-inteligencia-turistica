"""Snapshot JSON para tableros-bureau (Vercel no lee la DB directo)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_URL = "host=/var/run/postgresql port=5433 dbname=bureau_test user=julian connect_timeout=10"


def test_snapshot(monkeypatch, tmp_path):
    from backend import writer, export_snapshot
    monkeypatch.setenv("BACKEND_DATABASE_URL", TEST_URL)
    for k in ("GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    assert writer.run()["status"] == "ok"
    out = export_snapshot.run(str(tmp_path))
    marca = json.loads((tmp_path / "marca_llm.json").read_text())
    assert marca["dia"] != "" and len(marca["rows"]) >= 1
    assert out["files"] == ["informes.json", "marca_llm.json"]
