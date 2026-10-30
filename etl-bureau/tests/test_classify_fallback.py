"""Classify usa Gemini si Groq falla. TDD."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or {}
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)
    def json(self):
        return self._payload


def test_fallback_gemini(monkeypatch):
    from classify import llm_classify as C
    monkeypatch.setenv("GEMINI_API_KEY", "AQ_test")
    llamadas = []

    def fake_post(url, headers=None, json=None, timeout=None):
        llamadas.append(url)
        if "groq" in url:
            return _Resp(404)
        return _Resp(200, {"choices": [{"message": {"content": "[]"}}]})

    monkeypatch.setattr(C.requests, "post", fake_post)
    out, model = C._chat([{"role": "user", "content": "hola"}], "gsk_test")
    assert out == "[]"
    assert any("google" in u for u in llamadas)
