"""tieredtravel_med (TieredTravel sin key). TDD: parse fixture + columnas + run nunca levanta."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import tieredtravel_med  # noqa: E402


def test_parse_fixture_medellin_mas_otro():
    payload = [
        {"slug": "medellin", "name": "Medellín", "country": "Colombia",
         "costs": {"budget": 50, "mid": 100, "luxury": 250}},
        {"slug": "paris", "name": "Paris", "country": "France",
         "costs": {"budget": 120, "mid": 250, "luxury": 600}},
    ]
    df = tieredtravel_med.parse_destinations(payload, n_hoteles=10, n_atracciones=20)
    assert list(df.columns) == ["slug", "nombre", "pais", "costo_budget", "costo_mid",
                                "costo_luxury", "n_hoteles", "n_atracciones"]
    assert len(df) == 1
    assert df.iloc[0]["slug"] == "medellin"
    assert df.iloc[0]["pais"] == "Colombia"
    assert float(df.iloc[0]["costo_budget"]) == 50
    assert float(df.iloc[0]["costo_mid"]) == 100
    assert float(df.iloc[0]["costo_luxury"]) == 250
    assert int(df.iloc[0]["n_hoteles"]) == 10
    assert int(df.iloc[0]["n_atracciones"]) == 20


def test_parse_match_por_nombre_con_acento():
    payload = [{"slug": "somewhere", "name": "Medellín, Colombia", "country": "Colombia"}]
    df = tieredtravel_med.parse_destinations(payload)
    assert len(df) == 1
    assert df.iloc[0]["nombre"] == "Medellín, Colombia"


def test_parse_sin_match_fila_medellin_con_ceros_y_conteo_global():
    payload = [{"slug": "paris", "name": "Paris", "country": "France"}]
    df = tieredtravel_med.parse_destinations(payload, n_hoteles=7, n_atracciones=9)
    assert len(df) == 1  # nunca vacio sin carry
    assert df.iloc[0]["slug"] == "medellin"
    assert float(df.iloc[0]["costo_budget"]) == 0
    assert float(df.iloc[0]["costo_mid"]) == 0
    assert float(df.iloc[0]["costo_luxury"]) == 0
    assert int(df.iloc[0]["n_hoteles"]) == 7
    assert int(df.iloc[0]["n_atracciones"]) == 9


def test_columnas_exactas():
    assert tieredtravel_med.COLUMNS == ["slug", "nombre", "pais", "costo_budget", "costo_mid",
                                       "costo_luxury", "n_hoteles", "n_atracciones"]
    assert list(tieredtravel_med._empty().columns) == tieredtravel_med.COLUMNS


def test_run_nunca_levanta_con_red_rota(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    out = tieredtravel_med.run()  # no debe levantar
    assert isinstance(out, list)
