"""Gated Brand24 trial (S3). TDD: RED primero (sin keys -> SKIP, parse fixture)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import gated_brand24  # noqa: E402
from transform import kpis  # noqa: E402


# --- RED: sin keys ni manual -> SKIP honesto ---


def test_skip_sin_keys_ni_manual(monkeypatch, tmp_path):
    monkeypatch.delenv("BRAND24_KEY", raising=False)
    monkeypatch.delenv("BRAND24_ACCOUNT_ID", raising=False)
    monkeypatch.setattr(gated_brand24, "RAW", tmp_path)
    assert gated_brand24.run() in (False, None)


# --- RED: fallback manual CSV se copia a data/raw/<hoy>/ ---


def test_fallback_manual_csv(monkeypatch, tmp_path):
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / "brand24_export.csv").write_text(
        "periodo,fuente,sentimiento,alcance,fecha_consulta\n"
        "2026-10,twitter,neu,120,2026-10-31\n"
    )
    monkeypatch.delenv("BRAND24_KEY", raising=False)
    monkeypatch.delenv("BRAND24_ACCOUNT_ID", raising=False)
    monkeypatch.setattr(gated_brand24, "RAW", tmp_path)
    assert gated_brand24.run() is True
    outs = list(tmp_path.glob("*/brand24_menciones.csv"))
    assert outs and outs[0].stat().st_size > 0


# --- RED: parse fixture de menciones ---


def test_parse_mentions_fixture():
    payload = {
        "data": [
            {
                "title": "Medellín top destino",
                "source": "Twitter",
                "sentiment": "positive",
                "reach": 1500,
                "publishedAt": "2026-10-28T12:00:00Z",
            },
            {
                "title": "Bureau Medellín eventos",
                "source": "News",
                "sentiment": "negative",
                "reach": 300,
                "publishedAt": "2026-10-29T08:00:00Z",
            },
            {
                "title": "Turismo Medellín",
                "source": "twitter",
                "sentiment": "neutral",
                "reach": 50,
                "publishedAt": "2026-10-30T09:00:00Z",
            },
        ]
    }
    df = gated_brand24.parse_mentions(payload, "Medellín")
    assert {
        "periodo",
        "fuente",
        "sentimiento",
        "alcance",
        "fecha_consulta",
    } <= set(df.columns)
    assert len(df) == 3
    assert set(df["periodo"]) == {"2026-10"}
    assert set(df["sentimiento"]) == {"pos", "neg", "neu"}
    assert int(df["alcance"].sum()) == 1850


# --- GREEN: nunca levanta (error de red -> carry -> False) ---


def test_run_nunca_levanta(monkeypatch, tmp_path):
    import requests

    monkeypatch.setenv("BRAND24_KEY", "x")
    monkeypatch.setenv("BRAND24_ACCOUNT_ID", "1")
    calls = {}

    def fake_save(df, name, columns=None):
        calls["name"] = name
        return tmp_path / "brand24_fake.csv"

    monkeypatch.setattr(gated_brand24, "save_or_carry", fake_save)

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    assert gated_brand24.run() is False
    assert calls.get("name") == "brand24_menciones"


# --- KPIs: SKIP en 0 sin CSV, shares + sentimiento con fixture ---


def test_kpis_brand24_skip_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_brand24()
    assert out["brand24_menciones_total"] == 0
    assert out["brand24_sentimiento_neto"] == 0.0


def test_kpis_brand24_shares(monkeypatch):
    df = pd.DataFrame(
        [
            {"periodo": "2026-10", "fuente": "twitter", "sentimiento": "pos",
             "alcance": 100, "fecha_consulta": "2026-10-31"},
            {"periodo": "2026-10", "fuente": "twitter", "sentimiento": "pos",
             "alcance": 200, "fecha_consulta": "2026-10-31"},
            {"periodo": "2026-10", "fuente": "twitter", "sentimiento": "neu",
             "alcance": 50, "fecha_consulta": "2026-10-31"},
            {"periodo": "2026-10", "fuente": "news", "sentimiento": "neg",
             "alcance": 300, "fecha_consulta": "2026-10-31"},
        ]
    )
    monkeypatch.setattr(kpis, "latest_raw", lambda name: df)
    out = kpis.kpis_brand24()
    assert out["brand24_menciones_total"] == 4
    assert out["brand24_sentimiento_neto"] == 0.25  # (2-1)/4
    assert out["brand24_share_twitter"] == 0.75
    assert out["brand24_share_news"] == 0.25
    assert out["brand24_alcance_total"] == 650
    assert out["brand24_periodo"] == "2026-10"
