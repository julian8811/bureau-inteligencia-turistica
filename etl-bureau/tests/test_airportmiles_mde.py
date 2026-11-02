"""T1 (S3,S4): AirportMiles MDE/EOH. TDD."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import airportmiles_mde  # noqa: E402

COLUMNS = ["iata", "nombre", "ciudad", "pais", "lat", "lon", "fuente"]


def _fixture():
    return {
        "data": [
            {"iata": "MDE", "nombre": "José María Córdova", "ciudad": "Rionegro",
             "pais": "Colombia", "lat": 6.1645, "lon": -75.4231},
            {"iata": "EOH", "nombre": "Olaya Herrera", "ciudad": "Medellín",
             "pais": "Colombia", "lat": 6.2185, "lon": -75.5860},
            {"iata": "BOG", "nombre": "El Dorado", "ciudad": "Bogotá",
             "pais": "Colombia", "lat": 4.7016, "lon": -74.1469},
        ]
    }


def test_parse_fixture_2_aeropuertos():
    df = airportmiles_mde.parse_payload(_fixture())
    assert list(df.columns) == COLUMNS
    assert set(df["iata"]) == {"MDE", "EOH"}
    assert len(df) == 2
    assert (df["fuente"] == "airportmiles").all()


def test_parse_sin_mde_vacio():
    df = airportmiles_mde.parse_payload({"data": [{"iata": "BOG", "nombre": "El Dorado",
                                                   "ciudad": "Bogotá"}]})
    assert df.empty


def test_run_nunca_levanta_con_get_roto(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    out = airportmiles_mde.run()
    assert isinstance(out, list)
    assert len(out) == 1  # guarda (vacío o carry) pero nunca levanta


def test_columnas_exactas():
    assert airportmiles_mde.COLUMNS == COLUMNS
