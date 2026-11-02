"""openmeteo_ensemble (sin key, models=icon_seamless). TDD: parse fixture + columnas + run nunca levanta."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import openmeteo_ensemble  # noqa: E402


def _fixture():
    return {"daily": {
        "time": ["2026-11-03", "2026-11-04"],
        "temperature_2m_max_member00": [24.0, 25.0],
        "temperature_2m_max_member01": [26.0, 27.0],
        "temperature_2m_max_member02": [25.0, 26.0],
        "precipitation_sum_member00": [0.0, 5.0],
        "precipitation_sum_member01": [2.0, 8.0],
        "precipitation_sum_member02": [10.0, 2.0],
    }}


def test_parse_fixture_2dias_3members():
    df = openmeteo_ensemble.parse_ensemble(_fixture())
    assert list(df.columns) == ["date", "tmax_mean", "prec_mean", "prec_p10", "prec_p90", "n_members"]
    assert len(df) == 2
    assert df.iloc[0]["date"] == "2026-11-03"
    assert int(df.iloc[0]["n_members"]) == 3
    assert float(df.iloc[0]["tmax_mean"]) == 25.0
    assert abs(float(df.iloc[0]["prec_mean"]) - 4.0) < 1e-9
    assert float(df.iloc[0]["prec_p10"]) <= float(df.iloc[0]["prec_mean"]) <= float(df.iloc[0]["prec_p90"])
    assert float(df.iloc[1]["tmax_mean"]) == 26.0
    assert abs(float(df.iloc[1]["prec_mean"]) - 5.0) < 1e-9


def test_columnas_exactas():
    assert openmeteo_ensemble.COLUMNS == ["date", "tmax_mean", "prec_mean", "prec_p10", "prec_p90", "n_members"]
    assert list(openmeteo_ensemble._empty().columns) == openmeteo_ensemble.COLUMNS


def test_run_nunca_levanta_con_red_rota(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    out = openmeteo_ensemble.run()  # no debe levantar
    assert isinstance(out, list)
