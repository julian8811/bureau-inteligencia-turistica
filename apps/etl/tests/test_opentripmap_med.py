"""OpenTripMap Medellin (T3 S1-S3): POIs turisticos radio 30km. TDD: RED primero."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import opentripmap_med  # noqa: E402
from transform import kpis  # noqa: E402


# --- RED: sin key -> SKIP honesto ---

def test_skip_sin_key(monkeypatch):
    monkeypatch.delenv("OPENTRIPMAP_KEY", raising=False)
    assert opentripmap_med.run() is False


# --- RED: parse fixture ---

def test_parse_places_fixture():
    payload = [
        {"name": "Museo de Antioquia", "kinds": "cultural,museums",
         "point": {"lon": -75.568, "lat": 6.252}},
        {"name": "Cerro El Volador", "kinds": "natural",
         "point": {"lon": -75.592, "lat": 6.264}},
    ]
    df = opentripmap_med.parse_places(payload)
    assert len(df) == 2
    assert {"periodo", "nombre", "kinds", "lon", "lat", "fecha_consulta"} <= set(df.columns)
    assert df.iloc[0]["nombre"] == "Museo de Antioquia"
    assert float(df.iloc[0]["lon"]) == -75.568


def test_parse_places_vacio():
    df = opentripmap_med.parse_places([])
    assert df.empty
    assert {"periodo", "nombre", "kinds", "lon", "lat", "fecha_consulta"} <= set(df.columns)


# --- RED: nunca levanta ---

def test_run_nunca_levanta(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    monkeypatch.setenv("OPENTRIPMAP_KEY", "fake")
    assert opentripmap_med.run() is False


def test_run_http_error_es_skip(monkeypatch):
    import requests

    class R:
        status_code = 401

        def json(self):
            return {}

    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    monkeypatch.setenv("OPENTRIPMAP_KEY", "fake")
    assert opentripmap_med.run() is False


# --- KPIs: ceros sin CSV ---

def test_kpis_opentripmap_ceros_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_opentripmap()
    assert out["opentripmap_pois_total"] == 0
    assert out["opentripmap_top_kind"] == ""


# --- KPIs: con fixture ---

def test_kpis_opentripmap_con_fixture(monkeypatch):
    df = pd.DataFrame([
        {"nombre": "A", "kinds": "cultural,museums"},
        {"nombre": "B", "kinds": "natural"},
        {"nombre": "C", "kinds": "cultural,churches"},
    ])
    monkeypatch.setattr(kpis, "latest_raw", lambda name: df)
    out = kpis.kpis_opentripmap()
    assert out["opentripmap_pois_total"] == 3
    assert out["opentripmap_top_kind"] == "cultural"
