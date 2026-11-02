"""Gated AeroDataBox (MDE/EOH via RapidAPI, T1 S1-S3). TDD: RED primero (sin key -> SKIP, parse fixture)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import aerodatabox_mde  # noqa: E402
from transform import kpis  # noqa: E402


# --- RED: sin key -> SKIP honesto ---


def test_skip_sin_key(monkeypatch):
    monkeypatch.delenv("AERODATABOX_KEY", raising=False)
    monkeypatch.delenv("FLIGHTPOWERS_KEY", raising=False)
    assert aerodatabox_mde.run() is False


# --- RED: parse fixture status ---


def test_parse_status_fixture():
    payload = {
        "departures": [
            {
                "number": "AV 9310",
                "status": "Scheduled",
                "departure": {"scheduledTimeUtc": "2026-11-02T14:00Z"},
                "arrival": {"airport": {"iata": "BOG"}},
                "delayMinutes": 0,
            },
            {
                "number": "CM 200",
                "status": "Delayed",
                "departure": {"scheduledTimeUtc": "2026-11-02T15:30Z"},
                "arrival": {"airport": {"iata": "PTY"}},
                "delayMinutes": 45,
            },
        ]
    }
    df = aerodatabox_mde.parse_status(payload, "SKRG")
    assert {
        "aeropuerto",
        "vuelo",
        "origen",
        "destino",
        "estado",
        "programado",
        "retraso_min",
        "fecha_consulta",
    } <= set(df.columns)
    assert len(df) == 2
    assert set(df["aeropuerto"]) == {"SKRG"}
    assert set(df["destino"]) == {"BOG", "PTY"}
    assert int(df["retraso_min"].max()) == 45


# --- GREEN: nunca levanta ---


def test_run_nunca_levanta(monkeypatch):
    import requests

    monkeypatch.setenv("FLIGHTPOWERS_KEY", "x")
    monkeypatch.delenv("AERODATABOX_KEY", raising=False)

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(requests, "get", boom)
    assert aerodatabox_mde.run() is False


# --- KPIs: SKIP en 0 sin CSV, conteos con fixture ---


def test_kpis_aerodatabox_skip_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_aerodatabox()
    assert out["aerodatabox_vuelos_total"] == 0
    assert out["aerodatabox_retrasados"] == 0


def test_kpis_aerodatabox_conteos(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "aeropuerto": "SKRG",
                "vuelo": "AV 9310",
                "origen": "SKRG",
                "destino": "BOG",
                "estado": "Scheduled",
                "programado": "2026-11-02T14:00Z",
                "retraso_min": 0,
                "fecha_consulta": "2026-11-01",
            },
            {
                "aeropuerto": "SKRG",
                "vuelo": "CM 200",
                "origen": "SKRG",
                "destino": "PTY",
                "estado": "Delayed",
                "programado": "2026-11-02T15:30Z",
                "retraso_min": 45,
                "fecha_consulta": "2026-11-01",
            },
            {
                "aeropuerto": "SKMD",
                "vuelo": "CFC 1",
                "origen": "SKMD",
                "destino": "MDE",
                "estado": "Cancelled",
                "programado": "2026-11-02T16:00Z",
                "retraso_min": 0,
                "fecha_consulta": "2026-11-01",
            },
        ]
    )
    monkeypatch.setattr(kpis, "latest_raw", lambda name: df)
    out = kpis.kpis_aerodatabox()
    assert out["aerodatabox_vuelos_total"] == 3
    assert out["aerodatabox_retrasados"] == 2
    assert out["aerodatabox_aeropuertos"] == 2
