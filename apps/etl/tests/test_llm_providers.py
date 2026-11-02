"""Proveedores LLM: groq -> gemini -> cerebras -> mistral. TDD RED->GREEN."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

KEYS = ("GROQ_API_KEY", "GEMINI_API_KEY", "CEREBRAS_API_KEY", "MISTRAL_API_KEY")


def _limpiar_env(monkeypatch):
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)


def _doc_3sec(texto="Total 100"):
    return json.dumps({"secciones": [
        {"id": sid, "titulo": sid, "bullets": [{"texto": texto, "fuente": "F"}]}
        for sid in ("a", "b", "c")]})


def _llm_ok_payload():
    return {"choices": [{"message": {"content": "[]"}}]}


class _Ok:
    def __init__(self, content):
        self._content = content
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class _Err:
    def __init__(self, status):
        self.status_code = status

    def raise_for_status(self):
        import requests
        raise requests.HTTPError(f"{self.status_code} err")

    def json(self):
        return {}


def test_redactar_sin_keys_lista_vacia(monkeypatch):
    from report import redactar_informe as R
    _limpiar_env(monkeypatch)
    assert R._proveedores() == []


def test_redactar_orden_con_keys(monkeypatch):
    from report import redactar_informe as R
    _limpiar_env(monkeypatch)
    for k in KEYS:
        monkeypatch.setenv(k, "test_" + k.lower())
    nombres = [n for n, _, _, _ in R._proveedores()]
    assert nombres == ["groq", "gemini", "cerebras", "mistral"]


def test_redactar_404_pasa_al_siguiente(monkeypatch, tmp_path):
    from report import redactar_informe as R
    _limpiar_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("CEREBRAS_API_KEY", "csk_test")
    llamadas = []

    def fake_post(url, headers=None, json=None, timeout=None):
        llamadas.append(url)
        if "groq" in url:
            return _Err(404)
        return _Ok(_doc_3sec())

    monkeypatch.setattr(R.requests, "post", fake_post)
    res = R.run(str(tmp_path), contexto={"total": 100})
    assert res["status"] == "ok"
    assert any("groq" in u for u in llamadas)
    assert any("cerebras" in u for u in llamadas)


def test_redactar_429_no_tumba_cadena(monkeypatch, tmp_path):
    from report import redactar_informe as R
    _limpiar_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("MISTRAL_API_KEY", "msk_test")
    llamadas = []

    def fake_post(url, headers=None, json=None, timeout=None):
        llamadas.append(url)
        if "groq" in url:
            return _Err(429)
        return _Ok(_doc_3sec())

    monkeypatch.setattr(R.requests, "post", fake_post)
    res = R.run(str(tmp_path), contexto={"total": 100})
    assert res["status"] == "ok"
    assert any("mistral" in u for u in llamadas)


def test_classify_skip_sin_keys(monkeypatch):
    from classify import llm_classify as C
    _limpiar_env(monkeypatch)
    assert C.run() == []


def test_classify_orden_failover_hasta_mistral(monkeypatch):
    from classify import llm_classify as C
    _limpiar_env(monkeypatch)
    for k in KEYS:
        monkeypatch.setenv(k, "test_" + k.lower())
    monkeypatch.setattr(C.time, "sleep", lambda s: None)
    llamadas = []

    class _R404:
        status_code = 404

    class _ROk:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return _llm_ok_payload()

    def fake_post(url, headers=None, json=None, timeout=None):
        llamadas.append(url)
        if "mistral" in url:
            return _ROk()
        return _R404()

    monkeypatch.setattr(C.requests, "post", fake_post)
    C._chat([{"role": "user", "content": "hola"}], "test_groq_api_key")
    orden = []
    for u in llamadas:
        tag = ("groq" if "groq" in u else
               "gemini" if "google" in u else
               "cerebras" if "cerebras" in u else
               "mistral" if "mistral" in u else "?")
        if not orden or orden[-1] != tag:
            orden.append(tag)
    assert orden == ["groq", "gemini", "cerebras", "mistral"]


def test_classify_429_no_tumba_cadena(monkeypatch):
    from classify import llm_classify as C
    _limpiar_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setattr(C.time, "sleep", lambda s: None)
    n = {"i": 0}

    class _R:
        def __init__(self, status):
            self.status_code = status

        def raise_for_status(self):
            if self.status_code != 200:
                import requests
                raise requests.HTTPError(str(self.status_code))

        def json(self):
            return _llm_ok_payload()

    def fake_post(url, headers=None, json=None, timeout=None):
        n["i"] += 1
        return _R(200) if n["i"] > 1 else _R(429)

    monkeypatch.setattr(C.requests, "post", fake_post)
    texto, _ = C._chat([{"role": "user", "content": "hola"}], "gsk_test")
    assert texto == "[]"
    assert n["i"] == 2
