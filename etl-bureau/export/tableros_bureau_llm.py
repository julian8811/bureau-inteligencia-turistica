"""Adapter tableros-bureau (S1-S4): PROC del ETL Bureau -> JSON schema tableros-bureau.

Lee SOLO PROC de nuestro ETL (data/processed/: pais_dashboard.csv,
destinos_dashboard.csv, ult3m_pais.csv, marca_llm.csv, kpis_historico.csv)
y escribe en etl-bureau/export/tableros_bureau/:
  - paises_2025_2026.json: array {anio, pais, mercado, llegadas, salidas}
  - marca_llm_2025_2026.json: {categorias, top_topico_global, ventana}
  - manifiesto_bureau.json: {generado, piezas, errores, mercados}

Reglas: grano ANUAL declarado (no se inventan meses), mercado directo
Colombia/Estados Unidos/Mexico/Brasil y resto->Europa, pais en MAYUSCULAS,
ficha fuente/licencia en cada JSON, SKIP honesto por pieza (jamas levanta
excepcion), sin nuevas dependencias (solo stdlib). No se cablea al daily.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import urllib.parse
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
OUT = BASE / "export" / "tableros_bureau"

FUENTE = "ETL Bureau abierto (etl-bureau, data/processed)"
LICENCIA = "Datos abiertos procesados por el ETL Bureau; insumo Aerocivil/DANE abierto."
MERCADOS = ["Colombia", "Estados Unidos", "México", "Brasil", "Europa"]
# Mapeo S3: directos tal cual, resto -> Europa (documentado en nota).
_DIRECTOS = {
    "COLOMBIA": "Colombia",
    "ESTADOS UNIDOS": "Estados Unidos",
    "MEXICO": "México",
    "BRASIL": "Brasil",
}
NOTA_MERCADO = (
    "Mapeo de mercados: Colombia/Estados Unidos/Mexico/Brasil directos, "
    "resto de paises -> 'Europa' (bucket comparable de tableros-bureau)."
)
NOTA_GRANO = (
    "Grano ANUAL por anio (2025 cerrado, 2026 YTD/enero-junio segun PROC); "
    "tableros-bureau usa grano mensual: no se inventan meses."
)


def _mercado_de(pais_may: str) -> str:
    clave = (pais_may or "").upper().replace("É", "E").replace("Í", "I")
    return _DIRECTOS.get(clave, "Europa")


def _num(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(round(float(str(value).replace(",", "."))))
    except (TypeError, ValueError):
        return default


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def build_paises() -> tuple[dict, str | None]:
    """Devuelve (payload, error|None). Nunca levanta excepcion."""
    try:
        rows = _read_csv(PROC / "pais_dashboard.csv")
        if not rows:
            raise ValueError("pais_dashboard.csv vacio o sin filas")
        cols = set(rows[0].keys() or [])
        ano_ref = str(rows[0].get("ano_ref") or "2025").strip() or "2025"
        ano_ytd = str(rows[0].get("ano_ytd") or "2026").strip() or "2026"
        c_med_ref, c_sal_ref = f"med_{ano_ref}", f"sal_{ano_ref}"
        c_med_ytd, c_sal_ytd = f"med_{ano_ytd}_ytd", f"sal_{ano_ytd}_ytd"
        for c in (c_med_ref, c_sal_ref):
            if c not in cols:
                raise ValueError(f"columna esperada {c} ausente en pais_dashboard.csv")
        serie: list[dict] = []
        for r in rows:
            pais = str(r.get("pais") or "").strip().upper()
            if not pais:
                continue
            mercado = _mercado_de(pais)
            serie.append(
                {
                    "anio": int(ano_ref),
                    "pais": pais,
                    "mercado": mercado,
                    "llegadas": _num(r.get(c_med_ref)),
                    "salidas": _num(r.get(c_sal_ref)),
                }
            )
            if c_med_ytd in cols or c_sal_ytd in cols:
                serie.append(
                    {
                        "anio": int(ano_ytd),
                        "pais": pais,
                        "mercado": mercado,
                        "llegadas": _num(r.get(c_med_ytd)),
                        "salidas": _num(r.get(c_sal_ytd)),
                    }
                )
        serie.sort(key=lambda d: (d["anio"], d["mercado"], d["pais"]))
        payload = {
            "id": "paises_2025_2026",
            "fuente": FUENTE,
            "licencia": LICENCIA,
            "grano": "anual",
            "nota_grano": NOTA_GRANO,
            "nota_mercado": NOTA_MERCADO,
            "mercados": MERCADOS,
            "anios": sorted({d["anio"] for d in serie}),
            "serie": serie,
        }
        return payload, None
    except Exception as exc:  # SKIP honesto: jamas tumba el proceso
        return (
            {
                "id": "paises_2025_2026",
                "estado": "SKIP",
                "motivo": f"{type(exc).__name__}: {exc}",
                "fuente": FUENTE,
                "licencia": LICENCIA,
                "grano": "anual",
                "nota_grano": NOTA_GRANO,
                "serie": [],
            },
            f"paises: {exc}",
        )


def build_marca() -> tuple[dict, str | None]:
    """Devuelve (payload, error|None). Nunca levanta excepcion."""
    try:
        rows = _read_csv(PROC / "marca_llm.csv")
        if not rows:
            raise ValueError("marca_llm.csv vacio o ausente")
        categorias = []
        for r in rows:
            categorias.append(
                {
                    "categoria": str(r.get("categoria") or "").strip(),
                    "n": _num(r.get("n")),
                    "share": float(str(r.get("share") or 0).replace(",", ".")),
                    "sent_net": float(str(r.get("sent_net") or 0).replace(",", ".")),
                    "top_topico": str(r.get("top_topico") or "").strip(),
                }
            )
        categorias = [c for c in categorias if c["categoria"]]
        if not categorias:
            raise ValueError("marca_llm.csv sin categorias validas")
        categorias.sort(key=lambda c: c["n"], reverse=True)
        ventana = "2025-2026"
        try:  # ventana corriente desde kpis_historico si existe
            krows = _read_csv(PROC / "kpis_historico.csv")
            fechas = sorted(
                str(r.get("fecha") or "") for r in krows if (r.get("fecha") or "").strip()
            )
            if fechas:
                ventana = f"{fechas[0][:7]} a {fechas[-1][:7]}"
        except Exception:
            ventana = "2025-2026"  # SKIP parcial: sin kpis, ventana por defecto
        payload = {
            "id": "marca_llm_2025_2026",
            "fuente": FUENTE,
            "licencia": LICENCIA,
            "ventana": ventana,
            "categorias": categorias,
            "top_topico_global": categorias[0]["top_topico"],
            "n_total": sum(c["n"] for c in categorias),
        }
        return payload, None
    except Exception as exc:  # SKIP honesto
        return (
            {
                "id": "marca_llm_2025_2026",
                "estado": "SKIP",
                "motivo": f"{type(exc).__name__}: {exc}",
                "fuente": FUENTE,
                "licencia": LICENCIA,
                "ventana": "2025-2026",
                "categorias": [],
                "top_topico_global": None,
            },
            f"marca_llm: {exc}",
        )


def _medio_de(feed: str, link: str) -> str:
    """Etiqueta corta del medio: query del RSS de Google News o host del link."""
    try:
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(feed or "").query).get("q", [""])[0]
        if q:
            return urllib.parse.unquote_plus(q).strip()[:60]
    except Exception:
        pass
    try:
        return urllib.parse.urlsplit(link or "").netloc.replace("www.", "")[:60]
    except Exception:
        return ""


def build_prensa() -> tuple[dict, str | None]:
    """Menciones en prensa (Google News RSS): serie semanal + últimos titulares."""
    try:
        srows = _read_csv(PROC / "desglose_alertas_serie.csv")
        serie = [{"semana": r.get("fecha", ""), "n": _num(r.get("n"))} for r in srows if r.get("fecha")]
        serie = serie[-26:]
        if not serie:
            raise ValueError("desglose_alertas_serie.csv sin semanas con datos")
        mendoc = json.loads((BASE / "web" / "data" / "menciones.json").read_text(encoding="utf-8"))
        titulares = [
            {
                "fecha": str(r.get("fecha", "")),
                "titulo": str(r.get("titulo", "")),
                "medio": _medio_de(str(r.get("feed", "")), str(r.get("link", ""))),
                "link": str(r.get("link", "")),
            }
            for r in (mendoc if isinstance(mendoc, list) else [])
            if str(r.get("titulo", "")).strip()
        ][:15]
        krows = _read_csv(PROC / "kpis_historico.csv")
        sent = None
        if krows:
            try:
                sent = float(str(krows[-1].get("sentimiento_neto") or 0))
            except (TypeError, ValueError):
                sent = None
        payload = {
            "id": "prensa_medios",
            "fuente": "ETL Bureau (Google News RSS + Reddit, sin login)",
            "licencia": LICENCIA,
            "grano": "semanal",
            "generado": _dt.date.today().isoformat(),
            "ventana_serie": [serie[0]["semana"], serie[-1]["semana"]],
            "serie": serie,
            "titulares": titulares,
            "sentimiento_neto": sent,
            "n_total_menciones": sum(d["n"] for d in serie),
        }
        return payload, None
    except Exception as exc:  # SKIP honesto
        return (
            {"id": "prensa_medios", "estado": "SKIP",
             "motivo": f"{type(exc).__name__}: {exc}",
             "fuente": "ETL Bureau (Google News RSS + Reddit, sin login)",
             "licencia": LICENCIA, "grano": "semanal",
             "serie": [], "titulares": []},
            f"prensa: {exc}",
        )


def build_informe() -> tuple[dict, str | None]:
    """Lee export/informe_llm/informe_<corte>.json y lo deja en schema del tab Informes."""
    try:
        cands = sorted((BASE / "export" / "informe_llm").glob("informe_*.json"))
        if not cands:
            raise ValueError("sin informe_llm (corra report/redactar_informe.py)")
        doc = json.loads(cands[-1].read_text(encoding="utf-8"))
        secs = [x for x in doc.get("secciones", []) if x.get("bullets")]
        if not secs:
            raise ValueError("informe sin secciones con datos")
        return ({"corte": doc.get("corte", ""), "secciones": secs,
                 "fuente": FUENTE + " + redacción LLM verificada",
                 "licencia": LICENCIA, "estado": "ok"}, "")
    except Exception as exc:
        return ({"corte": "", "secciones": [], "estado": "skip"}, f"informe_llm: {exc}")


def _n(payload: dict, key: str = "serie") -> int:
    try:
        return len(payload.get(key) or payload.get("categorias") or [])
    except Exception:
        return 0


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    errores: list[str] = []
    piezas: list[dict] = []

    paises, err = build_paises()
    if err:
        errores.append(err)
    p = OUT / "paises_2025_2026.json"
    p.write_text(json.dumps(paises, ensure_ascii=False, indent=1), encoding="utf-8")
    piezas.append(
        {
            "archivo": "etl-bureau/export/tableros_bureau/paises_2025_2026.json",
            "id": "paises_2025_2026",
            "estado": paises.get("estado", "ok"),
            "n": _n(paises),
        }
    )
    print(f"[adapter] paises_2025_2026: {piezas[-1]['n']} filas -> {p}")

    marca, err = build_marca()
    if err:
        errores.append(err)
    p = OUT / "marca_llm_2025_2026.json"
    p.write_text(json.dumps(marca, ensure_ascii=False, indent=1), encoding="utf-8")
    piezas.append(
        {
            "archivo": "etl-bureau/export/tableros_bureau/marca_llm_2025_2026.json",
            "id": "marca_llm_2025_2026",
            "estado": marca.get("estado", "ok"),
            "n": _n(marca, "categorias"),
        }
    )
    print(f"[adapter] marca_llm_2025_2026: {piezas[-1]['n']} categorias -> {p}")

    prensa, err = build_prensa()
    if err:
        errores.append(err)
    p = OUT / "prensa_medios.json"
    p.write_text(json.dumps(prensa, ensure_ascii=False, indent=1), encoding="utf-8")
    piezas.append(
        {
            "archivo": "etl-bureau/export/tableros_bureau/prensa_medios.json",
            "id": "prensa_medios",
            "estado": prensa.get("estado", "ok"),
            "n": _n(prensa),
        }
    )
    print(f"[adapter] prensa_medios: {piezas[-1]['n']} semanas -> {p}")

    informe, err = build_informe()
    if err:
        errores.append(err)
    p = OUT / "informe_llm.json"
    p.write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    piezas.append(
        {
            "archivo": "etl-bureau/export/tableros_bureau/informe_llm.json",
            "id": "informe_llm",
            "estado": informe.get("estado", "ok"),
            "n": len(informe.get("secciones", [])),
        }
    )
    print(f"[adapter] informe_llm: {piezas[-1]['n']} secciones -> {p}")

    manifiesto = {
        "generado": _dt.date.today().isoformat(),
        "fuente": FUENTE,
        "licencia": LICENCIA,
        "piezas": piezas,
        "errores": errores,
        "mercados": MERCADOS,
        "nota": "Agregados PROC del ETL Bureau en schema tableros-bureau. " + NOTA_GRANO,
    }
    p = OUT / "manifiesto_bureau.json"
    p.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[adapter] manifiesto_bureau: {len(piezas)} piezas -> {p}")
    return 0


def run() -> list:
    """Entrada daily.py: regenera los 3 JSON y devuelve sus rutas."""
    main()
    return sorted(OUT.glob("*.json"))


if __name__ == "__main__":
    raise SystemExit(main())
