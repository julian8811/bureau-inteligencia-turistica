"""fx_cop (currency-api sin key). TDD: parse fixture + columnas + run nunca levanta."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import fx_cop  # noqa: E402


def test_parse_fixture_cop_eur():
    payload = {"date": "2026-11-01", "usd": {"cop": 3201, "eur": 0.89, "mxn": 17.5, "brl": 5.1}}
    df = fx_cop.parse_rates(payload)
    assert list(df.columns) == ["base", "date", "cop", "eur", "mxn", "brl"]
    assert len(df) == 1
    assert df.iloc[0]["base"] == "USD"
    assert df.iloc[0]["date"] == "2026-11-01"
    assert float(df.iloc[0]["cop"]) == 3201
    assert float(df.iloc[0]["eur"]) == 0.89


def test_columnas_exactas():
    assert fx_cop.COLUMNS == ["base", "date", "cop", "eur", "mxn", "brl"]
    assert list(fx_cop._empty().columns) == fx_cop.COLUMNS


def test_run_nunca_levanta_con_red_rota(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    out = fx_cop.run()  # no debe levantar
    assert isinstance(out, list)
