"""Socrata fase 2 (T2 S1-S3): operaciones jh8x-n6h6 + migrantes c4mm-qn8q. TDD: RED primero."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import socrata_migrantes, socrata_operaciones  # noqa: E402
from transform import kpis  # noqa: E402


# --- Operaciones: parse fixture ---

def test_operaciones_parse_fixture():
    payload = [
        {"aeropuerto": "MDE", "operaciones": "120", "a_o": "2025"},
        {"aeropuerto": "BOG", "operaciones": "300", "a_o": "2025"},
    ]
    df = socrata_operaciones.parse_operaciones(payload)
    assert len(df) == 2
    assert "aeropuerto" in df.columns
    assert "operaciones" in df.columns
    assert "fecha_consulta" in df.columns


def test_operaciones_skip_sin_datos(monkeypatch):
    monkeypatch.setattr(socrata_operaciones, "paginate_socrata", lambda *a, **k: pd.DataFrame())
    assert socrata_operaciones.run() is False


def test_operaciones_run_nunca_levanta(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    assert socrata_operaciones.run() is False


# --- Migrantes: parse fixture ---

def test_migrantes_parse_fixture():
    payload = [
        {"nacionalidad": "Venezuela", "total": "50", "a_o": "2025"},
        {"nacionalidad": "Ecuador", "total": "20", "a_o": "2025"},
    ]
    df = socrata_migrantes.parse_migrantes(payload)
    assert len(df) == 2
    assert "nacionalidad" in df.columns
    assert "total" in df.columns
    assert "fecha_consulta" in df.columns


def test_migrantes_skip_sin_datos(monkeypatch):
    monkeypatch.setattr(socrata_migrantes, "paginate_socrata", lambda *a, **k: pd.DataFrame())
    assert socrata_migrantes.run() is False


def test_migrantes_run_nunca_levanta(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    assert socrata_migrantes.run() is False


# --- KPIs: ceros sin CSV ---

def test_kpis_operaciones_ceros_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_operaciones()
    assert out["operaciones_total"] == 0
    assert out["operaciones_top_aeropuerto"] == ""


def test_kpis_migrantes_ceros_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_migrantes()
    assert out["migrantes_total"] == 0
    assert out["migrantes_top_nacionalidad"] == ""


# --- KPIs: con fixture ---

def test_kpis_operaciones_con_fixture(monkeypatch):
    df = pd.DataFrame([
        {"aeropuerto": "MDE", "operaciones": 120},
        {"aeropuerto": "BOG", "operaciones": 300},
        {"aeropuerto": "MDE", "operaciones": 30},
    ])
    monkeypatch.setattr(kpis, "latest_raw", lambda name: df)
    out = kpis.kpis_operaciones()
    assert out["operaciones_total"] == 450
    assert out["operaciones_top_aeropuerto"] == "BOG"


def test_kpis_migrantes_con_fixture(monkeypatch):
    df = pd.DataFrame([
        {"nacionalidad": "Venezuela", "total": 50},
        {"nacionalidad": "Ecuador", "total": 20},
        {"nacionalidad": "Venezuela", "total": 10},
    ])
    monkeypatch.setattr(kpis, "latest_raw", lambda name: df)
    out = kpis.kpis_migrantes()
    assert out["migrantes_total"] == 80
    assert out["migrantes_top_nacionalidad"] == "Venezuela"
