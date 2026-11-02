"""Gated FlightPowers (reemplazo Amadeus, S1-S4). TDD: RED primero (sin key -> SKIP, parse fixture)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import gated_flightpowers  # noqa: E402
from transform import kpis  # noqa: E402


# --- RED: sin key -> SKIP honesto ---


def test_skip_sin_key(monkeypatch):
    monkeypatch.delenv("FLIGHTPOWERS_KEY", raising=False)
    assert gated_flightpowers.run() is False


# --- RED: parse fixture oneway ---


def test_parse_offers_fixture():
    payload = {
        "data": [
            {
                "origin": "MDE",
                "destination": "MIA",
                "departure_date": "2026-12-10",
                "price": {"total": "420.50", "currency": "USD"},
            },
            {
                "origin": "MDE",
                "destination": "MIA",
                "departure_date": "2026-12-11",
                "price": {"total": "380.00", "currency": "USD"},
            },
        ]
    }
    df = gated_flightpowers.parse_offers(payload, "MDE", "MIA")
    assert {
        "periodo",
        "origen",
        "destino",
        "precio",
        "moneda",
        "fecha_consulta",
    } <= set(df.columns)
    assert len(df) == 2
    assert set(df["periodo"]) == {"2026-12"}
    assert set(df["origen"]) == {"MDE"}
    assert set(df["destino"]) == {"MIA"}
    assert float(df["precio"].min()) == 380.00
    assert set(df["moneda"]) == {"USD"}


# --- GREEN: nunca levanta ---


def test_run_nunca_levanta(monkeypatch):
    import requests

    monkeypatch.setenv("FLIGHTPOWERS_KEY", "x")

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(requests, "get", boom)
    assert gated_flightpowers.run() is False


# --- KPIs: SKIP en 0 sin CSV, medianas por ruta con fixture ---


def test_kpis_flightpowers_skip_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_flightpowers()
    assert out["flightpowers_ofertas_total"] == 0
    assert out["flightpowers_rutas"] == 0


# --- T1 hoteles: parse fixture + SKIP sin key ---


def test_parse_hotels_fixture():
    payload = {
        "data": [
            {
                "city": "Medellin",
                "hotel": "Hotel Poblado Plaza",
                "checkin": "2026-12-10",
                "price": {"total": "180.00", "currency": "USD"},
            },
            {
                "city": "Medellin",
                "hotel": "Hotel Laureles 70",
                "checkin": "2026-12-11",
                "price": {"total": "95.50", "currency": "USD"},
            },
        ]
    }
    df = gated_flightpowers.parse_hotels(payload, "Medellin")
    assert {
        "periodo",
        "ciudad",
        "hotel",
        "precio",
        "moneda",
        "fecha_consulta",
    } <= set(df.columns)
    assert len(df) == 2
    assert set(df["periodo"]) == {"2026-12"}
    assert set(df["ciudad"]) == {"Medellin"}
    assert float(df["precio"].min()) == 95.50
    assert set(df["moneda"]) == {"USD"}


def test_hotels_skip_sin_key(monkeypatch):
    monkeypatch.delenv("FLIGHTPOWERS_KEY", raising=False)
    assert gated_flightpowers.run_hotels() is False


def test_hotels_nunca_levanta(monkeypatch):
    import requests

    monkeypatch.setenv("FLIGHTPOWERS_KEY", "x")

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(requests, "get", boom)
    assert gated_flightpowers.run_hotels() is False


def test_kpis_hoteles_skip_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_hoteles()
    assert out["flightpowers_hoteles_total"] == 0


def test_kpis_hoteles_mediana(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "periodo": "2026-12",
                "ciudad": "Medellin",
                "hotel": "A",
                "precio": 180.0,
                "moneda": "USD",
                "fecha_consulta": "2026-10-31",
            },
            {
                "periodo": "2026-12",
                "ciudad": "Medellin",
                "hotel": "B",
                "precio": 95.5,
                "moneda": "USD",
                "fecha_consulta": "2026-10-31",
            },
        ]
    )
    monkeypatch.setattr(kpis, "latest_raw", lambda name: df)
    out = kpis.kpis_hoteles()
    assert out["flightpowers_hoteles_total"] == 2
    assert out["flightpowers_hoteles_mediana"] == 137.75
    assert out["flightpowers_hoteles_periodo"] == "2026-12"


def test_kpis_flightpowers_medianas(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "periodo": "2026-12",
                "origen": "MDE",
                "destino": "MIA",
                "precio": 380.0,
                "moneda": "USD",
                "fecha_consulta": "2026-10-31",
            },
            {
                "periodo": "2026-12",
                "origen": "MDE",
                "destino": "MIA",
                "precio": 420.0,
                "moneda": "USD",
                "fecha_consulta": "2026-10-31",
            },
            {
                "periodo": "2026-12",
                "origen": "MDE",
                "destino": "MEX",
                "precio": 310.0,
                "moneda": "USD",
                "fecha_consulta": "2026-10-31",
            },
        ]
    )
    monkeypatch.setattr(kpis, "latest_raw", lambda name: df)
    out = kpis.kpis_flightpowers()
    assert out["flightpowers_ofertas_total"] == 3
    assert out["flightpowers_rutas"] == 2
    assert out["flightpowers_periodo"] == "2026-12"
    assert out["flightpowers_mediana_MDE_MIA"] == 400.0
    assert out["flightpowers_mediana_MDE_MEX"] == 310.0
