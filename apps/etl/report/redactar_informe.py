"""Redacta informe narrativo estilo TEC con Groq desde el warehouse.

Lee PROC (kpis_historico, pais/destinos/ult3m_dashboard, marca_llm, desgloses),
pide a Groq bullets por seccion espejo TEC y valida que TODA cifra del texto
exista en el contexto (anti-alucinacion). Sin GROQ_API_KEY -> SKIP honesto.

Salida: export/informe_llm/informe_<corte>.json + upsert a backend.informes
(si hay BACKEND_DATABASE_URL). Uso: python3 -m report.redactar_informe [dir]
"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
OUT = BASE / "export" / "informe_llm"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_MODELS = ["gemini-3.6-flash"]

SECCIONES = [
    ("tendencias", "Tendencias", "trimestre movil, ocupacion y tarifa con YoY"),
    ("receptivo", "Turismo receptivo", "destinos top, share Medellin, YoY"),
    ("emisores", "Mercados emisores", "top paises emisores con YoY"),
    ("salidas", "Salidas de colombianos", "salidas al exterior ult3m con YoY"),
    ("conectividad", "Conectividad aérea", "pax MDE/EOH, rutas y carga top"),
    ("marca", "Marca y conversación digital", "categorias LLM, sentimiento, topico"),
    ("visitante", "Visitante EVI", "gasto, grupo de viaje, motivos y noches por ola"),
    ("aereo", "Detalle aéreo", "aeropuertos, aerolíneas e ICCA"),
    ("gestion", "Gestión Bureau", "captación, rueda de negocios, padrón y eventos (informe 2025)"),
    ("territorio", "Territorio y seguridad", "RNT, seguridad, clima, movilidad y género"),
]

SYSTEM = (
    "Redactas informes de turismo de Medellin y Colombia, estilo boletin TEC. "
    "Usas SOLO cifras del CONTEXTO JSON que te pasan; prohibido inventar, "
    "redondear o mezclar años. 2026 es el año en curso: el dato PRINCIPAL es el YTD/ult3m 2026 "
    "con su corte explícito (YTD o ventana); 2025 es el año cerrado de referencia para YoY. "
    "OBLIGATORIO: las secciones emisores y receptivo incluyen bullets con los totales YTD 2026 "
    "(emisores_ytd_2026, destinos_ytd_2026) citando 'YTD 2026'. "
    "Cada bullet es UNA ORACION COMPLETA de prosa "
    "institucional (sujeto + cifra con separador de miles + variacion YoY cuando "
    "exista + cierre interpretativo corto); PROHIBIDO el formato etiqueta "
    "sucinta tipo 'clave: valor (YoY x)'. Cada bullet cita su fuente en fuente. "
    "Por sección agregas 'analisis' (2-3 bullets que interpretan el dato: por qué "
    "importa, qué explica el cambio, con cifras del contexto) y 'grafico' "
    "(values en las unidades exactas del contexto: fracciones como 0.607, "
    "no porcentajes como 60.7) "
    "({'titulo', 'labels' (máx 10 categorías), 'values' (solo cifras del contexto), "
    "'unidad'}). Respondes SOLO un JSON {\"secciones\": [{\"id\", \"titulo\", "
    "\"bullets\": [{\"texto\", \"fuente\"}], \"analisis\": [{\"texto\", "
    "\"fuente\"}], \"grafico\": {\"titulo\", \"labels\", \"values\", "
    "\"unidad\"}}]}, sin texto extra, sin code fences."
)


TAB = Path("/tmp/tableros-bureau/data/open")


def _top1(rows: list, key: str) -> dict:
    """Fila con mayor valor en key ({} si vacía)."""
    if not rows:
        return {}
    try:
        return max(rows, key=lambda r: float(r.get(key) or 0))
    except (TypeError, ValueError):
        return {}


def _read(name: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(PROC / name)
        return df.fillna("")
    except Exception:
        return pd.DataFrame()


KPIS_CLAVE = ("fecha", "ano_ref", "med_ventana", "med_ult3m_total", "med_ult3m_yoy",
    "entradas_nacionalidad_ult3m", "salidas_destino_ult3m", "salidas_destino_ult3m_yoy",
    "aereo_mde_eoh_ult3m", "gasto_prom_dia_cop", "gasto_trimestre", "occ_med_ult",
    "occ_med_periodo", "tarifa_med_ult", "uplift_feria_pp", "menciones",
    "sentimiento_neto", "share_medellin", "pax_llegadas_mde", "carga_ult_kg",
    "llm_top_categoria", "llm_top_cat_share", "llm_sent_marca", "llm_share_seguridad",
    "llm_top_topico", "emisor_top1", "emisor_top1_med", "emisor_top5_share",
    "destino_med_share", "salidas_top_dest", "salidas_top_valor", "rutas_top1",
    "rnt_med_total", "hurtos_med_ult", "homicidios_med_ult", "lluvia_med_mm",
    "pm25_med", "pax_terminal_mes", "pax_metro_mes", "genero_entradas_fem",
    "genero_salidas_fem")


def _redondear(v):
    try:
        f = float(v)
        return round(f, 3)
    except (TypeError, ValueError):
        return v


def build_contexto() -> dict:
    ctx: dict = {}
    kpis = _read("kpis_historico.csv")
    if not kpis.empty:
        fila = kpis.iloc[-1]
        ctx.update({k: _redondear(fila[k]) for k in KPIS_CLAVE if k in fila})
    for name, key in (("pais_dashboard.csv", "emisores_top"),
                      ("destinos_dashboard.csv", "destinos"),
                      ("ult3m_pais.csv", "ult3m"),
                      ("marca_llm.csv", "marca_llm")):
        df = _read(name)
        if not df.empty:
            ctx[key] = [{k: _redondear(v) for k, v in r.items()}
                        for r in df.head(8).to_dict(orient="records")]
    ctx.update(_ytd_2026())
    for name, key in (("desglose_rutas_mde.csv", "rutas_top"),
                      ("desglose_carga_mde.csv", "carga")):
        df = _read(name)
        if not df.empty:
            ctx[key] = [{k: _redondear(v) for k, v in r.items()}
                        for r in df.head(5).to_dict(orient="records")]
    ctx.update(_bloques_tableros())
    pits = _read("desglose_pits.csv")
    if not pits.empty:
        ctx["pits_top"] = [{k: _redondear(v) for k, v in r.items()}
                           for r in pits.head(3).to_dict(orient="records")]
    return ctx


def _ytd_2026() -> dict:
    """Agregados YTD 2026 (año en curso): lo más fresco del warehouse."""
    ctx: dict = {}
    try:
        df = _read("pais_dashboard.csv")
        if "med_2026_ytd" in df.columns:
            ytd = df[["pais", "med_2026_ytd"]].dropna().sort_values("med_2026_ytd", ascending=False).head(8)  # type: ignore[call-overload]  # stubs pandas incompletos; verificado por ejecución
            ctx["emisores_ytd_2026"] = [{k: _redondear(v) for k, v in r.items()}
                                        for r in ytd.to_dict(orient="records")]
        df = _read("destinos_dashboard.csv")
        if "llegadas_2026_ytd" in df.columns:
            ytd = df[["ciudad", "llegadas_2026_ytd"]].dropna().sort_values("llegadas_2026_ytd", ascending=False).head(8)  # type: ignore[call-overload]  # stubs pandas incompletos; verificado por ejecución
            ctx["destinos_ytd_2026"] = [{k: _redondear(v) for k, v in r.items()}
                                        for r in ytd.to_dict(orient="records")]
    except Exception:
        pass
    return ctx


def _json_open(name: str):
    try:
        import json as _j
        return _j.loads((TAB / name).read_text(encoding="utf-8"))
    except Exception:
        return None


def _bloques_tableros() -> dict:
    """Lee agregados publicados de tableros-bureau (SKIP por bloque si faltan)."""
    ctx: dict = {}
    evi = _json_open("evi.json") or {}
    olas = evi.get("olas") or []
    if olas:
        o = olas[-1]
        g, m = _top1(o.get("grupo", []), "participacion"), _top1(o.get("motivos", []), "participacion")
        ctx["evi_ola"] = {k: _redondear(o.get(k, "")) for k in
                          ("ola", "n", "gasto_estadia_usd", "gasto_diario_usd", "noches")}
        ctx["evi_ola"]["top_grupo"] = g.get("nombre", "")
        ctx["evi_ola"]["top_grupo_share"] = _redondear(g.get("participacion", ""))
        ctx["evi_ola"]["top_motivo"] = m.get("nombre", "")
        ctx["evi_ola"]["top_motivo_share"] = _redondear(m.get("participacion", ""))
    con = _json_open("conectividad.json") or {}
    aero = con.get("aeropuertos") or []
    if aero:
        anio_max = max(r.get("anio", 0) for r in aero)
        top = sorted([r for r in aero if r.get("anio") == anio_max],
                     key=lambda r: r.get("llegadas", 0), reverse=True)[:5]
        ctx["aeropuertos_top"] = [{k: _redondear(r.get(k, "")) for k in
                                   ("aeropuerto", "anio", "llegadas")} for r in top]
    lineas = con.get("aerolineas") or []
    if lineas:
        anio_max = max(r.get("anio", 0) for r in lineas)
        top = sorted([r for r in lineas if r.get("anio") == anio_max],
                     key=lambda r: r.get("llegadas", 0), reverse=True)[:5]
        ctx["aerolineas_top"] = [{k: _redondear(r.get(k, "") or r.get("nombre", "")) for k in
                                  ("sigla", "nombre", "anio", "llegadas")} for r in top]
    icca = _json_open("icca.json") or {}
    if icca.get("ciudades"):
        ctx["icca"] = [{k: _redondear(c.get(k, "")) for k in
                        ("ciudad", "puesto", "reuniones")} for c in icca["ciudades"]]
    wiki = _json_open("wikipedia.json") or {}
    serie = wiki.get("serie") or []
    if serie:
        anio_max = max(r.get("anio", 0) for r in serie)
        cubo: dict = {}
        for r in serie:
            if r.get("anio") == anio_max:
                cubo[r.get("destino", "")] = cubo.get(r.get("destino", ""), 0) + (r.get("vistas", 0) or 0)
        ctx["wiki_top"] = [{"destino": d, "vistas": v} for d, v in
                           sorted(cubo.items(), key=lambda x: x[1], reverse=True)[:6]]
        ctx["wiki_anio"] = anio_max
    ctx.update(_gestion())
    return ctx


def _gestion() -> dict:
    """Lee window.INFORME (informe 2025) vía node. SKIP si falla."""
    import json as _j
    import subprocess
    try:
        out = subprocess.run(["node", "-e",
                              "var window={};require('/tmp/tableros-bureau/data/informe2025.js');"
                              "console.log(JSON.stringify(window.INFORME));"],
                             capture_output=True, text=True, timeout=20)
        inf = _j.loads(out.stdout or "{}")
    except Exception:
        return {}
    if not inf:
        return {}
    rueda = inf.get("rueda") or {}
    return {"gestion_2025": {
        "captados": inf.get("captados", ""), "internacionales": inf.get("internacionales", ""),
        "nacionales": inf.get("nacionales", ""), "impacto_usd": inf.get("impactoUsd", ""),
        "asistentes": inf.get("asistentes", ""), "miembros": inf.get("miembros", ""),
        "altas": inf.get("altas", ""), "satisfaccion": inf.get("satisfaccion", ""),
        "rueda_miembros": rueda.get("miembros", ""), "rueda_citas": rueda.get("citas", ""),
        "rueda_cumplieron": rueda.get("cumplieron", ""),
        "eventos_realizados": (inf.get("realizados") or {}).get("eventos", ""),
        "derrama_usd": (inf.get("realizados") or {}).get("derramaMillonesUsd", "")}}


def _candidatos(tok: str) -> set[float]:
    """Interpretaciones numéricas de un token (formatos es/co incluidos)."""
    t = tok.strip().rstrip(",.").lstrip("+-")
    es_pct = t.endswith("%")
    t = t.rstrip("%")
    vals: set[float] = set()

    def f(x: str):
        try:
            return float(x)
        except ValueError:
            return None

    if "." in t and "," in t:
        if re.match(r"^\d{1,3}(,\d{3})+\.\d+$", t):
            v = f(t.replace(",", ""))
        else:
            v = f(t.replace(".", "").replace(",", "."))
        if v is not None:
            vals.add(v)
    elif "," in t:
        ent, _, dec = t.rpartition(",")
        if dec and len(dec) <= 2 and ent.replace(".", "").isdigit():
            v = f(ent.replace(".", "") + "." + dec)
        else:
            v = f(t.replace(",", ""))
        if v is not None:
            vals.add(v)
    elif t.count(".") > 1:
        v = f(t.replace(".", ""))
        if v is not None:
            vals.add(v)
        ent, _, dec = t.rpartition(".")
        v2 = f(ent.replace(".", "") + "." + dec)
        if v2 is not None:
            vals.add(v2)
    elif t.count(",") > 1:
        v = f(t.replace(",", ""))
        if v is not None:
            vals.add(v)
        ent, _, dec = t.rpartition(",")
        v2 = f(ent.replace(",", "") + "." + dec)
        if v2 is not None:
            vals.add(v2)
    else:
        v = f(t)
        if v is not None:
            vals.add(v)
        if re.match(r"^\d{1,3}(\.\d{3})+$", t):
            v2 = f(t.replace(".", ""))
            if v2 is not None:
                vals.add(v2)
    if es_pct:
        vals |= {v / 100 for v in list(vals)}
    return vals


def _trivial(tok: str, cands: set[float]) -> bool:
    if "%" in tok or "." in tok or "," in tok:
        return False
    return bool(cands) and all(abs(v) < 100 for v in cands)


def _match(a: float, nums_ctx: list[float]) -> bool:
    # Misma cantidad en otra escala (fracción <-> porcentaje) y con otro signo
    # (el regex borra el "-" en texto y contexto: la dirección la da la prosa,
    # el validador exige la magnitud). Se prueban a, -a, a*100 y a/100.
    escalas = {a, -a, a * 100, a / 100, -a * 100, -a / 100} if a != 0 else {a}
    for v in escalas:
        for c in nums_ctx:
            if abs(c) >= 1:
                tol = max(0.051, 0.02 * abs(c))
            elif abs(c) >= 0.1:
                tol = max(0.011, 0.02 * abs(c))
            else:
                tol = 0.02 * abs(c) + 1e-9
            if abs(v - c) <= tol:
                return True
    return False


def _cifras_validas(doc: dict, ctx_dump: str) -> tuple[bool, str]:
    nums_ctx: list[float] = []
    for t in re.findall(r"\d[\d.,]*%?", ctx_dump):
        nums_ctx.extend(_candidatos(t))
    for sec in doc.get("secciones", []):
        textos = [b.get("texto", "") for b in sec.get("bullets", [])]
        textos += [b.get("texto", "") for b in sec.get("analisis", [])]
        for texto in textos:
            for tok in re.findall(r"\d[\d.,]*%?", texto):
                cands = _candidatos(tok)
                if not cands or _trivial(tok, cands):
                    continue
                if not any(_match(a, nums_ctx) for a in cands):
                    return False, tok
        graf = sec.get("grafico") or {}
        labels, values = (graf.get("labels") or [])[:10], (graf.get("values") or [])[:10]
        if values and len(labels) != len(values):
            return False, "grafico labels/values"
        for v in values:
            cands = _candidatos(str(v)) if isinstance(v, str) else {float(v)} if isinstance(v, (int, float)) else set()
            if not cands:
                return False, str(v)
            if not any(_match(a, nums_ctx) for a in cands):
                return False, str(v)
    return True, ""


def _proveedores():
    provs = []
    if os.environ.get("GROQ_API_KEY", ""):
        provs.append(("groq", GROQ_URL, os.environ["GROQ_API_KEY"], MODELS))
    if os.environ.get("GEMINI_API_KEY", ""):
        provs.append(("gemini", GEMINI_URL, os.environ["GEMINI_API_KEY"], GEMINI_MODELS))
    return provs


def _llamar(ctx_dump: str) -> dict:
    prompt = ("CONTEXTO JSON (única fuente de cifras):\n" + ctx_dump +
              "\n\nRedacta las secciones: " +
              ", ".join(f"{i} ({d})" for i, _, d in SECCIONES) +
              ". 3 a 6 bullets por sección con datos; si una sección no tiene datos, bullets [].")
    last = None
    for nombre, url, key, modelos in _proveedores():
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        for model in modelos:
            try:
                r = requests.post(url, headers=headers, timeout=90, json={
                    "model": model,
                    "messages": [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 6000,
                    "response_format": {"type": "json_object"}})
                r.raise_for_status()
                return json.loads(r.json()["choices"][0]["message"]["content"])
            except Exception as e:
                last = f"{nombre}/{model}: {e}"
    raise RuntimeError(f"LLM fallo en todos los proveedores ({last})")


def run(out_dir: str = "", contexto: dict | None = None) -> dict:
    if not _proveedores():
        print("[informe][SKIP] sin GROQ_API_KEY ni GEMINI_API_KEY")
        return {"status": "skip"}
    ctx = contexto if contexto is not None else build_contexto()
    if not ctx:
        print("[informe][SKIP] warehouse vacio")
        return {"status": "skip"}
    ctx_dump = json.dumps(ctx, ensure_ascii=False, default=str)
    try:
        doc = _llamar(ctx_dump)
    except Exception as e:
        print(f"[informe][SKIP] LLM no disponible ({e})")
        return {"status": "skip"}
    ok, tok = _cifras_validas(doc, ctx_dump)
    if not ok:
        print(f"[informe][INVALID] cifra sin fuente en contexto: {tok}")
        qdir = BASE / "export" / "informe_llm" / "cuarentena"
        qdir.mkdir(parents=True, exist_ok=True)
        (qdir / f"rechazado_{str(date.today().isoformat())}.json").write_text(
            json.dumps({"cifra": tok, "doc": doc}, ensure_ascii=False, indent=1))
        return {"status": "invalid", "cifra": tok}
    secs = []
    for s in doc.get("secciones", []):
        if not s.get("bullets"):
            continue
        secs.append({"id": s.get("id", ""), "titulo": s.get("titulo", ""),
                     "bullets": s.get("bullets", []),
                     "analisis": s.get("analisis", []),
                     "grafico": s.get("grafico") or {}})
    if len(secs) < 3:
        print("[informe][INVALID] menos de 3 secciones con datos")
        return {"status": "invalid", "cifra": ""}
    corte = str(date.today().isoformat())
    out = Path(out_dir) if out_dir else BASE / "export" / "informe_llm"
    out.mkdir(parents=True, exist_ok=True)
    informe = {"corte": corte, "generado": corte, "secciones": secs}
    dest = out / f"informe_{corte}.json"
    dest.write_text(json.dumps(informe, ensure_ascii=False, indent=1))
    web = BASE / "web" / "data" / "informe_llm.json"
    web.parent.mkdir(parents=True, exist_ok=True)
    web.write_text(json.dumps(informe, ensure_ascii=False, indent=1))
    _guardar_backend(corte, secs)
    return {"status": "ok", "path": str(dest), "secciones": len(secs)}


def _guardar_backend(corte: str, secs: list) -> None:
    try:
        sys.path.insert(0, str(BASE))
        from backend import db
        if not db.get_url():
            return
        con = db.connect()
        with con:
            with con.cursor() as cur:
                for s in secs:
                    payload = {"bullets": s.get("bullets", []),
                               "analisis": s.get("analisis", []),
                               "grafico": s.get("grafico") or {}}
                    cur.execute(
                        "INSERT INTO informes (corte, seccion, titulo, bullets) VALUES (%s, %s, %s, %s)"
                        " ON CONFLICT (corte, seccion) DO UPDATE SET titulo = EXCLUDED.titulo,"
                        " bullets = EXCLUDED.bullets, cifras = EXCLUDED.cifras, creado = now()",
                        (corte, s.get("id", ""), s.get("titulo", ""),
                         json.dumps(payload, ensure_ascii=False)))
        con.close()
    except Exception as e:
        print(f"[informe][WARN] backend no disponible ({e})")


if __name__ == "__main__":
    print(run(sys.argv[1] if len(sys.argv) > 1 else ""))
