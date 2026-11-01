# -*- coding: utf-8 -*-
"""Trae los agregados del ETL Bureau (repo bureau-inteligencia-turistica)
y los deja en data/open con el schema de este tablero. No toca las piezas
propias (icca/evi/huella/informe) ni reescribe conectividad/ema/wikipedia.
Si una fuente falla, el JSON anterior queda.
"""
import json
import traceback
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "open"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://raw.githubusercontent.com/julian8811/bureau-inteligencia-turistica/main/etl-bureau/export/tableros_bureau"
UA = {"User-Agent": "TablerosBureau/1.0"}
ERRORES = []


def bajar(nombre):
    url = BASE + "/" + nombre
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def guardar(nombre, payload):
    p = OUT / nombre
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("escribe", nombre)
    return p


def marca_llm():
    try:
        src = bajar("marca_llm_2025_2026.json")
    except Exception as exc:
        ERRORES.append("marca_llm: " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
        print("falla marca_llm, se conserva el anterior")
        return
    cats = src.get("categorias", [])
    serie = [
        {
            "categoria": c.get("categoria"),
            "n": c.get("n", 0),
            "share": c.get("share", 0),
            "sent_net": c.get("sent_net", 0),
            "top_topico": c.get("top_topico", ""),
        }
        for c in cats
    ]
    guardar("bureau_marca_llm.json", {
        "id": "marca-llm",
        "titulo": "Conversación digital clasificada por LLM",
        "fuente": "ETL Bureau (alerts_rss + prensa_rss, Groq) " + str(src.get("ventana", "")),
        "url": BASE + "/marca_llm_2025_2026.json",
        "licencia": "Agregados propios del ETL; titulares de sus medios originales.",
        "universo": "Titulares de la ventana corriente clasificados en MICE/vacacional/marca/seguridad/clima/infraestructura/otro.",
        "serie": serie,
        "top_topico_global": src.get("top_topico_global", ""),
        "n_total": src.get("n_total", sum(c.get("n", 0) for c in cats)),
    })
    print("marca_llm", len(serie), "categorias")


def paises():
    try:
        src = bajar("paises_2025_2026.json")
    except Exception as exc:
        ERRORES.append("paises: " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
        print("falla paises, se conserva el anterior")
        return
    serie = src.get("serie", src if isinstance(src, list) else [])
    guardar("bureau_paises_2025_2026.json", {
        "id": "bureau-paises",
        "titulo": "Emisores 2025-2026 (ETL Bureau, grano anual)",
        "fuente": "ETL Bureau, pais_dashboard (Socrata Migración/Aerocivil)",
        "url": BASE + "/paises_2025_2026.json",
        "licencia": "Agregados propios del ETL; fuente primaria datos.gov.co.",
        "universo": "Grano anual declarado; no reemplaza la serie mensual de conectividad.",
        "grano": "anual",
        "serie": serie,
    })
    print("paises", len(serie), "filas")


def manifiesto():
    try:
        previo = json.loads((OUT / "manifiesto.json").read_text(encoding="utf-8"))
    except Exception:
        previo = {"generado": "", "piezas": [], "errores": []}
    piezas = [x for x in previo.get("piezas", []) if not str(x.get("archivo", "")).startswith("bureau_")]
    for nombre, pid, clave in (
        ("bureau_marca_llm.json", "marca-llm", "serie"),
        ("bureau_paises_2025_2026.json", "bureau-paises", "serie"),
    ):
        path = OUT / nombre
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        piezas.append({
            "archivo": "data/open/" + nombre,
            "id": pid,
            "estado": "ok",
            "n": len(payload.get(clave, []) or []),
        })
    doc = dict(previo)
    doc["piezas"] = piezas
    doc["errores"] = (previo.get("errores", []) + ERRORES)[-20:]
    (OUT / "manifiesto.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("manifiesto", [(x["id"], x["n"]) for x in piezas if str(x["id"]).startswith("marca") or str(x["id"]).startswith("bureau")])


if __name__ == "__main__":
    marca_llm()
    paises()
    manifiesto()
