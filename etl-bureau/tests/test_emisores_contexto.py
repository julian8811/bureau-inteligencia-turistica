"""Emisores contexto (T2 S3+S5): Graph Countries raw sin key. TDD: RED primero."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import emisores_contexto  # noqa: E402


def _fixture():
    return [
        {
            "cca3": "USA",
            "name": {"common": "United States"},
            "region": "Americas",
            "currencies": {"USD": {"name": "United States dollar", "symbol": "$"}},
            "languages": {"eng": "English"},
            "borders": ["CAN", "MEX"],
        },
        {
            "cca3": "COL",
            "name": {"common": "Colombia"},
            "region": "Americas",
            "currencies": {"COP": {"name": "Colombian peso", "symbol": "$"}},
            "languages": {"spa": "Spanish"},
            "borders": ["BRA", "ECU", "PAN", "PER", "VEN"],
        },
    ]


def test_parse_fixture_dos_paises():
    df = emisores_contexto.parse_countries(_fixture())
    assert len(df) == 2
    assert list(df.columns) == ["cca3", "nombre", "region", "moneda", "idiomas", "fronteras"]
    usa = df[df["cca3"] == "USA"].iloc[0]
    assert usa["nombre"] == "United States"
    assert usa["region"] == "Americas"
    assert usa["moneda"] == "USD"
    assert usa["idiomas"] == "English"
    assert usa["fronteras"] == "CAN,MEX"
    col = df[df["cca3"] == "COL"].iloc[0]
    assert col["moneda"] == "COP"
    assert col["idiomas"] == "Spanish"


def test_parse_columnas_exactas_vacio():
    df = emisores_contexto.parse_countries([])
    assert list(df.columns) == ["cca3", "nombre", "region", "moneda", "idiomas", "fronteras"]


def test_run_nunca_levanta_con_red_rota(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    out = emisores_contexto.run()
    assert isinstance(out, list)
