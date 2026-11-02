"""Fuentes WARN 01-nov (S1-S2): endurecer sin cambiar contrato.

TDD: RED primero contra el codigo viejo, GREEN tras el fix.
Contrato intacto: mismo CSV, SKIP/carry, jamas levantar.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import (
    aerocivil_flota,
    gastronomia_nocturna,
    ideam_clima,
    opensky_mde,
    wb_receipts,
)  # noqa: E402

# --- 1) wb_receipts: retry corto + filtrar vacios ---


def _wb_ok(status=200):
    class R:
        status_code = status

        def raise_for_status(self):
            if self.status_code == 429:
                raise Exception("429 Too Many Requests")

        def json(self):
            return [
                None,
                [{"country": {"value": "Colombia"}, "date": "2024", "value": 100}],
            ]

    return R()


def test_wb_retry_429_luego_ok(monkeypatch):
    calls = []

    def fake_get(*a, **k):
        calls.append(k)
        return _wb_ok(429) if len(calls) == 1 else _wb_ok(200)

    monkeypatch.setattr(wb_receipts.requests, "get", fake_get)
    monkeypatch.setattr("time.sleep", lambda s: None)
    df = wb_receipts.run_indicator("COL", "ST.INT.RCPT.CD")
    assert len(calls) >= 2, "debe reintentar tras 429"
    assert len(df) == 1, "tras retry exitoso hay dato"


def test_wb_concat_filtra_vacios(monkeypatch):
    import warnings

    full = pd.DataFrame(
        [
            {
                "countryiso3code": "COL",
                "country": "C",
                "year": "2024",
                "value": 1,
                "indicator": "i",
            }
        ]
    )
    first = True

    def fake_run_indicator(c, i):
        nonlocal first
        if first:
            first = False
            return full
        return wb_receipts._empty()

    monkeypatch.setattr(wb_receipts, "run_indicator", fake_run_indicator)
    saved = {}
    monkeypatch.setattr(
        wb_receipts,
        "save_or_carry",
        lambda df, name, cols: saved.setdefault("df", df) or Path("x"),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        wb_receipts.run()
    assert len(saved["df"]) == 1


def test_wb_nunca_levanta(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(wb_receipts.requests, "get", boom)
    monkeypatch.setattr("time.sleep", lambda s: None)
    assert wb_receipts.run_indicator("COL", "ST.INT.RCPT.CD").empty
    monkeypatch.setattr(wb_receipts, "save_or_carry", lambda *a, **k: Path("x"))
    wb_receipts.run()


# --- 2) ideam lluvia: primer intento sin $order ---


def test_ideam_lluvia_primero_sin_order(monkeypatch):
    calls = []

    def fake_paginate(dataset, params, **kw):
        calls.append(dict(params))
        return pd.DataFrame([{"a": 1}])

    monkeypatch.setattr(ideam_clima, "paginate_socrata", fake_paginate)
    monkeypatch.setattr(ideam_clima, "save_or_carry", lambda df, name: Path(name))
    ideam_clima.run_lluvia()
    assert calls, "debe consultar"
    assert "$order" not in calls[0], f"primer intento sin $order, fue {calls[0]}"


def test_ideam_lluvia_skip_intacto(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("timeout s54a-sgyg offset=0")

    monkeypatch.setattr(ideam_clima, "paginate_socrata", boom)
    monkeypatch.setattr(ideam_clima, "save_or_carry", lambda df, name: Path(name))
    assert ideam_clima.run_lluvia() == Path("ideam_lluvia_med")


# --- 3) aerocivil: primer intento SIN $order ---


def test_aerocivil_primer_intento_sin_order(monkeypatch):
    calls = []

    def fake_paginate(dataset, params, **kw):
        calls.append(dict(params))
        return pd.DataFrame([{"a_o": 2024}])

    monkeypatch.setattr(aerocivil_flota, "paginate_socrata", fake_paginate)
    df = aerocivil_flota.run_ruta()
    assert calls, "debe consultar"
    assert "$order" not in calls[0], f"primer intento sin $order, fue {calls[0]}"
    assert len(calls) == 1, "sin segundo intento redundante si el primero trae dato"
    assert not df.empty


def test_aerocivil_nunca_levanta(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(aerocivil_flota, "paginate_socrata", boom)
    assert aerocivil_flota.run_ruta().empty


# --- 4) gastronomia: OSM intento unico corto ---


def test_gastro_osm_intento_unico_corto(monkeypatch):
    calls = []

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"elements": []}

    def fake_post(*a, **k):
        calls.append(k)
        return R()

    monkeypatch.setattr(gastronomia_nocturna.requests, "post", fake_post)
    monkeypatch.setattr(
        gastronomia_nocturna, "save_or_carry", lambda df, name: Path(name)
    )
    gastronomia_nocturna.run_osm_gastronomia()
    assert len(calls) == 1, f"OSM intento unico, fueron {len(calls)}"
    assert calls[0].get("timeout", 99) <= 15, (
        f"timeout corto, fue {calls[0].get('timeout')}"
    )


def test_gastro_osm_fail_no_tumba_y_alumbrado_intacto(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("overpass muerto")

    monkeypatch.setattr(gastronomia_nocturna.requests, "post", boom)
    monkeypatch.setattr(
        gastronomia_nocturna, "save_or_carry", lambda df, name: Path(name)
    )
    assert gastronomia_nocturna.run_osm_gastronomia() == Path("gastronomia_osm_med")
    assert gastronomia_nocturna.ALUMBRADO_CANDIDATOS == ["5upz-u2vi"]


# --- 5) opensky: states-only, 429 -> ventana menor ---


def test_opensky_429_reintenta_ventana_menor(monkeypatch):
    seen = []

    class R429:
        status_code = 429

    class Rok:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"states": []}

    def fake_get(url, params=None, **k):
        seen.append(dict(params or {}))
        return R429() if len(seen) == 1 else Rok()

    monkeypatch.setattr(opensky_mde.requests, "get", fake_get)
    monkeypatch.setattr(opensky_mde, "save_or_carry", lambda *a, **k: Path("x"))
    assert opensky_mde.run() is True
    assert len(seen) == 2, "tras 429 reintenta una vez"
    w0 = seen[0]["lamax"] - seen[0]["lamin"]
    w1 = seen[1]["lamax"] - seen[1]["lamin"]
    assert w1 < w0, "segundo intento con ventana menor"


def test_opensky_states_only_sin_flights(monkeypatch):
    src = Path(opensky_mde.__file__).read_text()
    assert opensky_mde.STATES.endswith("/api/states/all")
    assert "FUERA" in src, "documentado que /flights queda fuera"
    seen_urls = []

    class Rok:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"states": []}

    def fake_get(url, params=None, **k):
        seen_urls.append(url)
        return Rok()

    monkeypatch.setattr(opensky_mde.requests, "get", fake_get)
    monkeypatch.setattr(opensky_mde, "save_or_carry", lambda *a, **k: Path("x"))
    assert opensky_mde.run() is True
    assert seen_urls and all(u == opensky_mde.STATES for u in seen_urls), (
        f"solo states, sin /flights: {seen_urls}"
    )
