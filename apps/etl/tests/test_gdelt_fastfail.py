"""GDELT fast-fail (fuentes-warn-dead-skip T2 S3): 429 -> SKIP rapido, 1 solo intento.

TDD: RED primero contra el gdelt_marca con backoffs 120s+300s.
Sleeps y requests van mockeados: ningun test duerme de verdad.
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import gdelt_marca  # noqa: E402


def _http_429(*a, **k):
    resp = requests.models.Response()
    resp.status_code = 429
    raise requests.exceptions.HTTPError("429 Client Error: Too Many Requests", response=resp)


def _ok_timeline(*a, **k):
    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"timeline": [{"data": [{"date": "2026-10-25", "value": 42}]}]}

    return R()


def _patch_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(gdelt_marca.time, "sleep", lambda s: slept.append(s))
    return slept


def _patch_carry(monkeypatch):
    calls = []
    monkeypatch.setattr(
        gdelt_marca, "save_or_carry", lambda df, name, columns=None: calls.append((df, name)) or Path("x.csv")
    )
    return calls


def test_429_un_solo_intento_sin_backoff_largo(monkeypatch):
    calls = {"n": 0}

    def counting_429(*a, **k):
        calls["n"] += 1
        return _http_429(*a, **k)

    monkeypatch.setattr(gdelt_marca.requests, "get", counting_429)
    slept = _patch_sleep(monkeypatch)
    carried = _patch_carry(monkeypatch)

    gdelt_marca.run()

    assert calls["n"] == 1, f"esperaba 1 solo intento ante 429, hubo {calls['n']}"
    assert not [s for s in slept if s >= 30], f"backoff largo ante 429: {slept}"
    assert sum(slept) == 0, f"ante 429 no se duerme nada, se durmio {slept}"
    assert carried and carried[0][0].empty and carried[0][1] == "gdelt_marca"


def test_error_red_un_solo_reintento_corto(monkeypatch):
    seq = {"n": 0}

    def flaky(*a, **k):
        seq["n"] += 1
        if seq["n"] == 1:
            raise requests.exceptions.ConnectionError("sin red")
        return _ok_timeline(*a, **k)

    monkeypatch.setattr(gdelt_marca.requests, "get", flaky)
    slept = _patch_sleep(monkeypatch)
    carried = _patch_carry(monkeypatch)

    gdelt_marca.run()

    assert seq["n"] == 2
    assert slept == [5], f"reintento unico de 5s, fue {slept}"
    assert not carried[0][0].empty


def test_error_red_persistente_skip_tras_reintento(monkeypatch):
    calls = {"n": 0}

    def down(*a, **k):
        calls["n"] += 1
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(gdelt_marca.requests, "get", down)
    slept = _patch_sleep(monkeypatch)
    carried = _patch_carry(monkeypatch)

    gdelt_marca.run()  # jamas levanta

    assert calls["n"] == 2, f"maximo 2 intentos (1+1 reintento), hubo {calls['n']}"
    assert slept == [5]
    assert carried and carried[0][0].empty


def test_ok_primer_intento_sin_dormir(monkeypatch):
    calls = {"n": 0}

    def ok(*a, **k):
        calls["n"] += 1
        return _ok_timeline(*a, **k)

    monkeypatch.setattr(gdelt_marca.requests, "get", ok)
    slept = _patch_sleep(monkeypatch)
    carried = _patch_carry(monkeypatch)

    gdelt_marca.run()

    assert calls["n"] == 1
    assert slept == []
    assert not carried[0][0].empty
