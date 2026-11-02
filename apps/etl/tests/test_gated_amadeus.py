"""Gated Amadeus dev (S2). TDD: RED primero (sin keys -> SKIP, parse fixture)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import gated_amadeus  # noqa: E402
from transform import kpis  # noqa: E402


# --- RED: sin keys -> SKIP honesto ---


def test_skip_sin_keys(monkeypatch):
    monkeypatch.delenv("AMADEUS_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_SECRET", raising=False)
    assert gated_amadeus.run() is False


# --- RED: parse fixture flight-dates ---


def test_parse_flight_dates_fixture():
    payload = {
        "data": [
            {
                "type": "flight-date",
                "origin": "MDE",
                "destination": "MAD",
                "departureDate": "2026-12-10",
                "returnDate": "2026-12-20",
                "price": {"total": "2450.00", "currency": "COP"},
            },
            {
                "type": "flight-date",
                "origin": "MDE",
                "destination": "MAD",
                "departureDate": "2026-12-11",
                "price": {"total": "2300.00", "currency": "COP"},
            },
        ]
    }
    df = gated_amadeus.parse_flight_dates(payload, "MDE", "MAD")
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
    assert set(df["destino"]) == {"MAD"}
    assert float(df["precio"].min()) == 2300.00
    assert set(df["moneda"]) == {"COP"}


def test_parse_hotel_offers_fixture():
    payload = {
        "data": [
            {
                "hotel": {"hotelId": "MDE001", "name": "Hotel X"},
                "offers": [
                    {
                        "checkInDate": "2026-11-15",
                        "price": {"total": "320000", "currency": "COP"},
                    }
                ],
            },
        ]
    }
    df = gated_amadeus.parse_hotel_offers(payload, "MDE")
    assert {
        "periodo",
        "origen",
        "destino",
        "precio",
        "moneda",
        "fecha_consulta",
    } <= set(df.columns)
    assert len(df) == 1
    assert df.iloc[0]["periodo"] == "2026-11"
    assert float(df.iloc[0]["precio"]) == 320000.0


# --- GREEN: nunca levanta ---


def test_run_nunca_levanta(monkeypatch):
    import requests

    monkeypatch.setenv("AMADEUS_KEY", "x")
    monkeypatch.setenv("AMADEUS_SECRET", "y")

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(requests, "get", boom)
    assert gated_amadeus.run() is False


# --- KPIs: SKIP en 0 sin CSV, medianas por ruta con fixture ---


def test_kpis_amadeus_skip_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_amadeus()
    assert out["amadeus_ofertas_total"] == 0
    assert out["amadeus_rutas"] == 0


def test_kpis_amadeus_medianas(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "periodo": "2026-12",
                "origen": "MDE",
                "destino": "MAD",
                "precio": 2300.0,
                "moneda": "COP",
                "fecha_consulta": "2026-10-31",
            },
            {
                "periodo": "2026-12",
                "origen": "MDE",
                "destino": "MAD",
                "precio": 2500.0,
                "moneda": "COP",
                "fecha_consulta": "2026-10-31",
            },
            {
                "periodo": "2026-12",
                "origen": "MDE",
                "destino": "MIA",
                "precio": 1200.0,
                "moneda": "COP",
                "fecha_consulta": "2026-10-31",
            },
        ]
    )
    monkeypatch.setattr(kpis, "latest_raw", lambda name: df)
    out = kpis.kpis_amadeus()
    assert out["amadeus_ofertas_total"] == 3
    assert out["amadeus_rutas"] == 2
    assert out["amadeus_periodo"] == "2026-12"
    assert out["amadeus_mediana_MDE_MAD"] == 2400.0
    assert out["amadeus_mediana_MDE_MIA"] == 1200.0
