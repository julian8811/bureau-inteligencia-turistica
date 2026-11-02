"""Fuentes P1 (EMA + Ticketmaster + OpenSky). TDD: RED primero."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import dane_ema, opensky_mde, ticketmaster_eventos  # noqa: E402


# --- T1: DANE EMA ---

def test_ema_candidate_urls_patron_real():
    urls = dane_ema.candidate_urls()
    assert urls, "sin URLs candidatas"
    assert urls[0].startswith("https://www.dane.gov.co/files/operaciones/EMA/anex-EMA-")
    assert urls[0].endswith(".xlsx")


def _ema_fixture_xlsx(tmp_path) -> bytes:
    # formato real del anexo: filas Año/Meses x columnas de regiones
    df = pd.DataFrame([
        ["Año", "Meses", "Total nacional", "Antioquia"],
        [2026, "Julio", -7.5, -3.1],
        ["", "Agosto", -11.8, -4.78],
    ])
    xlsx = tmp_path / "anex-EMA-ago2026.xlsx"
    df.to_excel(xlsx, index=False, header=False, sheet_name="1.1 V.A Ing.real")
    return xlsx.read_bytes()


def test_ema_parse_minimo(tmp_path):
    long = dane_ema.parse_ema(_ema_fixture_xlsx(tmp_path), "https://x/anex-EMA-ago2026.xlsx")
    assert {"periodo", "indicador", "valor", "fuente_url", "hoja", "fecha_consulta"} <= set(long.columns)
    ant = long[long["indicador"].str.contains("Antioquia", na=False)]
    assert not ant.empty
    assert set(ant["periodo"]) == {"2026-07", "2026-08"}
    assert float(ant[ant["periodo"] == "2026-08"]["valor"].iloc[0]) == -4.78  # type: ignore[attr-defined]


def test_ema_run_nunca_levanta(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    assert dane_ema.run() is False


# --- T2: Ticketmaster ---

def test_tm_skip_sin_key(monkeypatch):
    monkeypatch.delenv("TICKETMASTER_KEY", raising=False)
    assert ticketmaster_eventos.run() is False


def test_tm_parse_fixture():
    payload = {"_embedded": {"events": [{
        "name": "Concierto X",
        "url": "https://tkt.mx/x",
        "dates": {"start": {"localDate": "2026-11-20"}},
        "classifications": [{"segment": {"name": "Music"}}],
        "_embedded": {"venues": [{"name": "Estadio", "city": {"name": "Medellín"}}]},
    }]}}
    df = ticketmaster_eventos.parse_events(payload)
    assert len(df) == 1
    assert df.iloc[0]["nombre"] == "Concierto X"
    assert df.iloc[0]["fecha"] == "2026-11-20"
    assert "fecha_consulta" in df.columns


def test_tm_run_nunca_levanta(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    monkeypatch.setenv("TICKETMASTER_KEY", "fake")
    assert ticketmaster_eventos.run() is False


# --- T3: OpenSky ---

def test_opensky_429_es_skip(monkeypatch):
    import requests

    class R:
        status_code = 429
        def json(self): return {}

    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    assert opensky_mde.run() is False


def test_opensky_parse_states():
    payload = {"states": [
        ["abc123", "AVA123  ", "Colombia", 1, 2, -75.6, 6.2, 9000, False, 250, 180, 0, None, 9000, "1234", False, 0],
    ]}
    df = opensky_mde.parse_states(payload)
    assert len(df) == 1
    assert df.iloc[0]["vuelo"] == "AVA123"
    assert float(df.iloc[0]["lat"]) == 6.2
    assert "fecha_consulta" in df.columns


def test_opensky_run_nunca_levanta(monkeypatch):
    import requests

    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", boom)
    assert opensky_mde.run() is False


# --- T5 (S1-S4): fixes sin keys que no tumban el daily ---

def test_ema_meses_completos():
    assert dane_ema.MESES == ["ene", "feb", "mar", "abr", "may", "jun",
                               "jul", "ago", "sep", "oct", "nov", "dic"]


def test_ema_parse_xlsx_real():
    p = Path(__file__).resolve().parents[1] / "data" / "raw" / "2026-10-30" / "dane_ema.xlsx"
    if not p.exists():
        pytest.skip("sin fixture real data/raw/2026-10-30/dane_ema.xlsx")
    df = dane_ema.parse_ema(p.read_bytes(), "https://www.dane.gov.co/files/operaciones/EMA/anex-EMA-ago2026.xlsx")
    assert len(df) > 1000
    assert str(df["periodo"].max()) >= "2026-08"
    assert df["indicador"].str.contains("Antioquia", na=False).any()


def test_eurostat_aviation_solo_paoc():
    from extract import eurostat_aviation
    assert eurostat_aviation.DATASETS == ["avia_paoc"]


def test_eurostat_demanda_solo_ttmd():
    from extract import eurostat_demanda
    assert eurostat_demanda.DATASETS == ["tour_dem_ttmd"]


def test_metro_movilidad_run_solo_metro(monkeypatch):
    from extract import metro_movilidad
    calls: list[str] = []
    monkeypatch.setattr(metro_movilidad, "run_metro_pasajeros",
                         lambda: calls.append("metro") or Path("metro"))

    def boom():
        calls.append("terminales")
        raise AssertionError("run_terminales no debe correr en el daily")

    monkeypatch.setattr(metro_movilidad, "run_terminales", boom)
    assert metro_movilidad.run() == [Path("metro")]
    assert calls == ["metro"]
