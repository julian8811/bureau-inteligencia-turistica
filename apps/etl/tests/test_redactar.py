"""Redactor LLM de informes estilo TEC. TDD: RED primero."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


@pytest.fixture(autouse=True)
def _base_tmp(monkeypatch, tmp_path):
    import report.redactar_informe as R
    (tmp_path / "web" / "data").mkdir(parents=True)
    monkeypatch.setattr(R, "BASE", tmp_path)


class _Resp:
    def __init__(self, content):
        self._content = content
    def raise_for_status(self):
        pass
    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _doc_con_bullet(texto):
    return json.dumps({"secciones": [
        {"id": sid, "titulo": sid,
         "bullets": [{"texto": texto, "fuente": "Migración Colombia"}]}
        for sid in ("receptivo", "emisores", "conectividad")]})


def _llm_ok(monkeypatch):
    from report import redactar_informe as R
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    for k in ("GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(k, raising=False)

    def fake_post(url, headers=None, json=None, timeout=None):
        import re
        prompt = json["messages"][-1]["content"]
        toks = re.findall(r"\d[\d.,]*", prompt)
        cifra = max(toks, key=lambda t: len(re.sub(r"[^\d]", "", t)))
        return _Resp(_doc_con_bullet(f"Medellín recibió {cifra} visitantes"))

    monkeypatch.setattr(R.requests, "post", fake_post)
    return R


def test_skip_sin_key(monkeypatch, tmp_path):
    import report.redactar_informe as R
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    res = R.run(str(tmp_path))
    assert res["status"] == "skip"


def test_redacta_y_valida_cifras(monkeypatch, tmp_path):
    R = _llm_ok(monkeypatch)
    res = R.run(str(tmp_path), contexto={"llegadas_medellin_2025": 123456})
    assert res["status"] == "ok"
    doc = json.loads(Path(res["path"]).read_text())
    assert doc["secciones"] and "123456" in doc["secciones"][0]["bullets"][0]["texto"]


def test_espejo_web_data(monkeypatch, tmp_path):
    import report.redactar_informe as R
    from tests.test_redactar import _llm_ok
    R2 = _llm_ok(monkeypatch)
    base_real = R2.BASE
    monkeypatch.setattr(R2, "BASE", tmp_path)
    res = R2.run("", contexto={"llegadas_medellin_2025": 123456})
    assert res["status"] == "ok"
    espejo = tmp_path / "web" / "data" / "informe_llm.json"
    assert json.loads(espejo.read_text())["corte"] == res["path"].split("informe_")[-1].replace(".json", "")
    monkeypatch.setattr(R2, "BASE", base_real)


def test_rechaza_cifra_inventada(monkeypatch, tmp_path):
    from report import redactar_informe as R
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    def fake_post(url, headers=None, json=None, timeout=None):
        return _Resp(_doc_con_bullet("Medellín recibió 999888777 visitantes"))

    monkeypatch.setattr(R.requests, "post", fake_post)
    res = R.run(str(tmp_path), contexto={"llegadas_medellin_2025": 123456})
    assert res["status"] == "invalid"
    assert not list(tmp_path.glob("*.json"))


def _run_con_texto(monkeypatch, tmp_path, texto, contexto):
    from report import redactar_informe as R
    from tests.test_redactar import _doc_con_bullet
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    def fake_post(url, headers=None, json=None, timeout=None):
        from tests.test_redactar import _Resp
        secs = [{"id": sid, "titulo": sid,
                 "bullets": [{"texto": texto, "fuente": "F"}]}
                for sid in ("a", "b", "c")]
        import json as _j
        return _Resp(_j.dumps({"secciones": secs}))

    monkeypatch.setattr(R.requests, "post", fake_post)
    return R.run(str(tmp_path), contexto=contexto)


def test_valida_miles_formato_es(monkeypatch, tmp_path):
    res = _run_con_texto(monkeypatch, tmp_path,
                         "Medellín recibió 247.331 visitantes",
                         {"total": 247331})
    assert res["status"] == "ok"


def test_valida_porcentaje_desde_fraccion(monkeypatch, tmp_path):
    res = _run_con_texto(monkeypatch, tmp_path,
                         "El share es 60,7%",
                         {"share": 0.607})
    assert res["status"] == "ok"


def test_valida_miles_formato_anglo(monkeypatch, tmp_path):
    from tests.test_redactar import _run_con_texto
    res = _run_con_texto(monkeypatch, tmp_path,
                         "La tarifa es 442,227.145 pesos",
                         {"tarifa": 442227.145})
    assert res["status"] == "ok"


def test_parser_ignora_coma_trailing():
    import report.redactar_informe as R
    assert R._candidatos("202310.0,") == {202310.0}
    assert 247331.0 in R._candidatos("247.331,")
    assert R._candidatos("60,7%,") == {60.7, 0.607}


def _doc_full(cifra_txt, valor):
    import json as _j
    return _j.dumps({"secciones": [
        {"id": sid, "titulo": sid,
         "bullets": [{"texto": f"Total {cifra_txt} visitantes", "fuente": "F"}],
         "analisis": [{"texto": f"Suba de {cifra_txt} por temporada", "fuente": "F"}],
         "grafico": {"titulo": "Top", "labels": ["Medellín"], "values": [valor], "unidad": "vis"}}
        for sid in ("a", "b", "c")]})


def test_informe_con_analisis_y_grafico(monkeypatch, tmp_path):
    from report import redactar_informe as R
    from tests.test_redactar import _Resp
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    def fake_post(url, headers=None, json=None, timeout=None):
        return _Resp(_doc_full("247.331", 247331))

    monkeypatch.setattr(R.requests, "post", fake_post)
    res = R.run(str(tmp_path), contexto={"total": 247331})
    assert res["status"] == "ok"
    import json as _j
    doc = _j.loads(__import__("pathlib").Path(res["path"]).read_text())
    sec = doc["secciones"][0]
    assert sec["analisis"] and sec["grafico"]["values"] == [247331]


def test_rechaza_grafico_inventado(monkeypatch, tmp_path):
    from report import redactar_informe as R
    from tests.test_redactar import _Resp
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    def fake_post(url, headers=None, json=None, timeout=None):
        return _Resp(_doc_full("100", 777666555))

    monkeypatch.setattr(R.requests, "post", fake_post)
    res = R.run(str(tmp_path), contexto={"total": 100})
    assert res["status"] == "invalid"


def test_valida_fraccion_contra_porcentaje(monkeypatch, tmp_path):
    from tests.test_redactar import _run_con_texto
    res = _run_con_texto(monkeypatch, tmp_path,
                         "La ocupación fue 0,67108",
                         {"occ": 67.108})
    assert res["status"] == "ok"


def test_valida_signo_como_direccion(monkeypatch, tmp_path):
    from tests.test_redactar import _run_con_texto
    res = _run_con_texto(monkeypatch, tmp_path,
                         "El sentimiento cayó a -0,478",
                         {"sent": -0.478})
    assert res["status"] == "ok"


def test_pide_json_object(monkeypatch, tmp_path):
    from report import redactar_informe as R
    from tests.test_redactar import _Resp, _doc_con_bullet
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    visto = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        visto.update(json)
        import re
        toks = re.findall(r"\d[\d.,]*", json["messages"][-1]["content"])
        cifra = max(toks, key=lambda t: len(re.sub(r"[^\d]", "", t)))
        return _Resp(_doc_con_bullet(f"Total {cifra}"))
    # OJO: este fake devuelve 1 sola sección -> el mínimo de 3 lo rechaza;
    # solo verificamos el payload enviado.
    monkeypatch.setattr(R.requests, "post", fake_post)
    R.run(str(tmp_path), contexto={"total": 100})
    assert visto.get("response_format") == {"type": "json_object"}


def test_valida_grafico_negativo(monkeypatch, tmp_path):
    import json as _j
    from report import redactar_informe as R
    from tests.test_redactar import _Resp
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    def fake_post(url, headers=None, json=None, timeout=None):
        doc = {"secciones": [
            {"id": sid, "titulo": sid,
             "bullets": [{"texto": "Total 100", "fuente": "F"}],
             "analisis": [],
             "grafico": {"titulo": "G", "labels": ["A"], "values": [-0.07], "unidad": "yoy"}}
            for sid in ("a", "b", "c")]}
        return _Resp(_j.dumps(doc))

    monkeypatch.setattr(R.requests, "post", fake_post)
    res = R.run(str(tmp_path), contexto={"yoy": -0.07, "total": 100})
    assert res["status"] == "ok"


def test_valida_casi_porcentaje(monkeypatch, tmp_path):
    from tests.test_redactar import _run_con_texto
    res = _run_con_texto(monkeypatch, tmp_path,
                         "Bogotá concentra casi 35%",
                         {"share": 0.3581})
    assert res["status"] == "ok"


def test_rechaza_porcentaje_lejano(monkeypatch, tmp_path):
    from tests.test_redactar import _run_con_texto
    res = _run_con_texto(monkeypatch, tmp_path,
                         "El share es 50%",
                         {"share": 0.607})
    assert res["status"] == "invalid"


def test_secciones_completas():
    import report.redactar_informe as R
    ids = [s[0] for s in R.SECCIONES]
    assert len(ids) == 10 and len(set(ids)) == 10
    for esperado in ("visitante", "aereo", "gestion", "territorio"):
        assert esperado in ids


def test_top1():
    import report.redactar_informe as R
    assert R._top1([{"n": "a", "v": 1}, {"n": "b", "v": 9}], "v")["n"] == "b"
    assert R._top1([], "v") == {}


def test_contexto_nuevo():
    import pytest
    import report.redactar_informe as R
    ctx = R.build_contexto()
    if "evi_ola" not in ctx or "gestion_2025" not in ctx or "icca" not in ctx:
        pytest.skip("sin /tmp/tableros-bureau (evi/icca/gestion no publicados en este env)")
    assert ctx["evi_ola"]["gasto_estadia_usd"] == 929.28
    assert ctx["gestion_2025"]["captados"] == 103
    assert ctx["icca"][2]["ciudad"] == "Medellín"


def test_valida_multipunto_ultimo_decimal(monkeypatch, tmp_path):
    from tests.test_redactar import _run_con_texto
    res = _run_con_texto(monkeypatch, tmp_path,
                         "La tarifa es 442.227.145 pesos",
                         {"tarifa": 442227.145})
    assert res["status"] == "ok"


def _doc_3sec(texto):
    import json as _j
    return _j.dumps({"secciones": [
        {"id": sid, "titulo": sid, "bullets": [{"texto": texto, "fuente": "F"}]}
        for sid in ("a", "b", "c")]})


def test_fallback_gemini(monkeypatch, tmp_path):
    from report import redactar_informe as R
    from tests.test_redactar import _Resp
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GEMINI_API_KEY", "AQ_test")
    llamadas = []

    def fake_post(url, headers=None, json=None, timeout=None):
        llamadas.append(url)
        if "groq" in url:
            raise RuntimeError("429 groq")
        return _Resp(_doc_3sec("Total 100"))

    monkeypatch.setattr(R.requests, "post", fake_post)
    res = R.run(str(tmp_path), contexto={"total": 100})
    assert res["status"] == "ok"
    assert any("groq" in u for u in llamadas) and any("google" in u for u in llamadas)


def test_sin_proveedores_es_skip(monkeypatch, tmp_path):
    from report import redactar_informe as R
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert R.run(str(tmp_path))["status"] == "skip"


def test_contexto_trae_ytd_2026():
    import report.redactar_informe as R
    ctx = R.build_contexto()
    assert ctx["emisores_ytd_2026"][0]["pais"] == "Estados Unidos"
    assert ctx["destinos_ytd_2026"][0]["ciudad"] == "Bogotá, D.C."


def test_valida_grafico_string_formateado(monkeypatch, tmp_path):
    import json as _j
    from report import redactar_informe as R
    from tests.test_redactar import _Resp
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    def fake_post(url, headers=None, json=None, timeout=None):
        doc = {"secciones": [
            {"id": sid, "titulo": sid,
             "bullets": [{"texto": "Total 100", "fuente": "F"}],
             "analisis": [],
             "grafico": {"titulo": "G", "labels": ["A"], "values": ["442.227.145"], "unidad": "cop"}}
            for sid in ("a", "b", "c")]}
        return _Resp(_j.dumps(doc))

    monkeypatch.setattr(R.requests, "post", fake_post)
    res = R.run(str(tmp_path), contexto={"tarifa": 442227.145, "total": 100})
    assert res["status"] == "ok"


def test_redactar_en_daily():
    src = __import__("pathlib").Path("etl-bureau/orchestration/daily.py").read_text() \
        if __import__("pathlib").Path("etl-bureau/orchestration/daily.py").exists() \
        else open("/home/julian/Bureau/etl-bureau/orchestration/daily.py").read()
    assert "redactar_informe.run" in src
