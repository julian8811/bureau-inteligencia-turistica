"""Conectividad y benchmarks -> tableros-bureau (T4, S3-S5).

Lee RAW de data/raw/<FECHA>/ y publica
export/tableros_bureau/conectividad_benchmark_2025_2026.json.
Solo stdlib + pandas. UTF-8. Defensivo: archivo ausente o vacio ->
bloque omitido con nota + estado ok si hay nucleo, skip si no hay
nada; exit 0, nunca tumba. No toca /tmp/tableros-bureau ni ningun
otro repo.

Nota de estilo: pandas solo se usa para cargar el CSV; toda la
agregacion es Python puro sobre registros dict para no depender de
los stubs de tipos de pandas.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW_DIR = BASE / "data" / "raw" / "2026-11-02"
OUT = BASE / "export" / "tableros_bureau" / "conectividad_benchmark_2025_2026.json"
FUENTE = "ETL Bureau, Aerocivil/terminales/DANE/Eurostat/WB/Wikimedia"
GENERADO = date.today().isoformat()

_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def _per(s: str) -> str:
    """Normaliza un periodo a YYYY-MM (raw trae YYYYMM o YYYYMMDDHH)."""
    t = re.sub(r"\D", "", s)
    if len(t) >= 6 and "1900" <= t[:4] <= "2100" and "01" <= t[4:6] <= "12":
        return f"{t[:4]}-{t[4:6]}"
    m = re.fullmatch(r"(\d{4})-(\d{2})(-\d{2})?", s.strip())
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return s.strip()

MESES_ES = {
    "ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04",
    "MAYO": "05", "JUNIO": "06", "JULIO": "07", "AGOSTO": "08",
    "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12",
}


def _records(name: str) -> list[dict[str, Any]] | None:
    """Carga un CSV del RAW como lista de dicts; None si ausente/vacio/header-only."""
    p = RAW_DIR / name
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        df = pd.read_csv(p, dtype=str, keep_default_na=False, engine="python")
    except Exception:
        return None
    if df.empty:
        return None
    cols = [str(c) for c in list(df.columns)]
    rows: list[dict[str, Any]] = []
    for vals in df.values.tolist():
        row = {c: (v.strip() if isinstance(v, str) else v) for c, v in zip(cols, vals, strict=False)}
        rows.append(row)
    if not rows:
        return None
    return rows


def _num(s: Any) -> float | None:
    s = str(s or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _int(v: float | None) -> int:
    return int(v) if v is not None else 0


def _oferta(notas: list[str]) -> dict[str, Any]:
    rows = _records("aerocivil_flota.csv")
    if rows is None:
        notas.append("oferta_aerea: aerocivil_flota.csv ausente o vacio, bloque omitido")
        return {"top_rutas": []}
    if not {"origen", "destino", "sillas_ofrecidas", "n_mero_de_vuelos"}.issubset(rows[0].keys()):
        notas.append("oferta_aerea: columnas esperadas ausentes, bloque omitido")
        return {"top_rutas": []}
    acc: dict[str, list[float]] = {}
    for r in rows:
        o = str(r.get("origen", "")).strip()
        d = str(r.get("destino", "")).strip()
        if not o or not d:
            continue
        ruta = f"{o}-{d}"
        s = _num(r.get("sillas_ofrecidas")) or 0.0
        v = _num(r.get("n_mero_de_vuelos")) or 0.0
        if ruta in acc:
            acc[ruta][0] += s
            acc[ruta][1] += v
        else:
            acc[ruta] = [s, v]
    if not acc:
        notas.append("oferta_aerea: sin filas validas, bloque omitido")
        return {"top_rutas": []}
    top = sorted(acc.items(), key=lambda kv: kv[1][0], reverse=True)[:10]
    return {
        "top_rutas": [
            {"ruta": ruta, "sillas": int(s), "vuelos": int(v)}
            for ruta, (s, v) in top
        ]
    }


def _operaciones(notas: list[str]) -> list[dict[str, Any]]:
    rows = _records("operaciones_aereas.csv")
    if rows is None:
        notas.append("operaciones: operaciones_aereas.csv ausente o vacio, bloque omitido")
        return []
    if not {"anio", "mes", "totaloperaciones"}.issubset(rows[0].keys()):
        notas.append("operaciones: columnas esperadas ausentes, bloque omitido")
        return []
    acc: dict[str, float] = {}
    for r in rows:
        n = _num(r.get("totaloperaciones"))
        if n is None:
            continue
        periodo = f"{str(r.get('anio', '')).strip()}-{str(r.get('mes', '')).strip().zfill(2)}"
        acc[periodo] = acc.get(periodo, 0.0) + n
    if not acc:
        notas.append("operaciones: sin filas validas, bloque omitido")
        return []
    return [{"periodo": p, "operaciones": int(v)} for p, v in sorted(acc.items())]


def _terrestre(notas: list[str]) -> list[dict[str, Any]]:
    rows = _records("terminales_med.csv")
    if rows is None:
        notas.append("terrestre: terminales_med.csv ausente o vacio, bloque omitido")
        return []
    if not {"a_o", "mes", "vehiculos", "pasajeros"}.issubset(rows[0].keys()):
        notas.append("terrestre: columnas esperadas ausentes, bloque omitido")
        return []
    acc: dict[str, list[float]] = {}
    for r in rows:
        pax = _num(r.get("pasajeros"))
        veh = _num(r.get("vehiculos"))
        if pax is None and veh is None:
            continue
        mm = MESES_ES.get(str(r.get("mes", "")).strip().upper(), "00")
        periodo = f"{str(r.get('a_o', '')).strip()}-{mm}"
        cur = acc.get(periodo, [0.0, 0.0])
        cur[0] += pax or 0.0
        cur[1] += veh or 0.0
        acc[periodo] = cur
    if not acc:
        notas.append("terrestre: sin filas validas, bloque omitido")
        return []
    return [
        {"periodo": p, "pasajeros": int(v[0]), "vehiculos": int(v[1])}
        for p, v in sorted(acc.items())
    ]


def _metro(notas: list[str]) -> list[dict[str, Any]]:
    rows = _records("movilidad_metro_med.csv")
    if rows is None:
        notas.append("metro: movilidad_metro_med.csv ausente o vacio, bloque omitido")
        return []
    if not {"pas_periodo", "pas_valor"}.issubset(rows[0].keys()):
        notas.append("metro: columnas esperadas ausentes, bloque omitido")
        return []
    acc: dict[str, float] = {}
    for r in rows:
        per = _per(str(r.get("pas_periodo", "").strip()))
        v = _num(r.get("pas_valor"))
        if not per or v is None:
            continue
        acc[per] = acc.get(per, 0.0) + v
    if not acc:
        notas.append("metro: sin filas validas, bloque omitido")
        return []
    return [{"periodo": p, "valor": int(v)} for p, v in sorted(acc.items())]


def _trm(notas: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rows = _records("trm_co.csv")
    if rows is not None and {"date", "rate_cop"}.issubset(rows[0].keys()):
        for r in rows:
            v = _num(r.get("rate_cop"))
            dt = str(r.get("date", "")).strip()
            if dt and v is not None:
                out.append({"date": dt, "cop_per_usd": v})
    else:
        notas.append("trm: trm_co.csv ausente o sin columnas esperadas, sub-bloque omitido")
    rows2 = _records("fx_cop.csv")
    if rows2 is not None and {"date", "cop"}.issubset(rows2[0].keys()):
        for r in rows2:
            v = _num(r.get("cop"))
            dt = str(r.get("date", "")).strip()
            if dt and v is not None:
                out.append({"date": dt, "cop_per_usd": v})
    else:
        notas.append("trm: fx_cop.csv ausente o sin columnas esperadas, sub-bloque omitido")
    if not out:
        notas.append("trm: sin filas validas, bloque omitido")
    out.sort(key=lambda d: str(d["date"]))
    return out


def _costos(notas: list[str]) -> list[dict[str, Any]]:
    rows = _records("tieredtravel_med.csv")
    if rows is None:
        notas.append("costos: tieredtravel_med.csv ausente o vacio, bloque omitido")
        return []
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        for k in ("costo_budget", "costo_mid", "costo_luxury", "n_hoteles", "n_atracciones"):
            if k in row:
                v = _num(row[k])
                row[k] = v if v is None else (int(v) if v.is_integer() else v)
        out.append(row)
    return out


def _bench_eu(notas: list[str]) -> list[dict[str, Any]]:
    spec = [
        ("eurostat_arrivals.csv", "arrivals", "eurostat_arrivals"),
        ("eurostat_aviation.csv", "passengers", "eurostat_aviation"),
        ("eurostat_capacity.csv", "value", "eurostat_capacity"),
        ("eurostat_demanda.csv", "value", ""),
        ("eurostat_tourism.csv", "nights", "eurostat_tourism"),
    ]
    out: list[dict[str, Any]] = []
    for fname, vcol, ds_fixed in spec:
        rows = _records(fname)
        if rows is None:
            notas.append(f"benchmark_eu: {fname} ausente o vacio, sub-bloque omitido")
            continue
        if not {"geo", "time", vcol}.issubset(rows[0].keys()):
            notas.append(f"benchmark_eu: {fname} sin columnas esperadas, sub-bloque omitido")
            continue
        for r in rows:
            v = _num(r.get(vcol))
            if v is None:
                continue
            try:
                anio = int(str(r.get("time", "")).strip()[:4])
            except ValueError:
                continue
            ds = ds_fixed or str(r.get("dataset", fname)).strip()
            out.append({"geo": str(r.get("geo", "")).strip(), "anio": anio,
                        "valor": v, "dataset": ds})
    if not out:
        notas.append("benchmark_eu: sin filas validas, bloque omitido")
    out.sort(key=lambda d: (str(d["dataset"]), str(d["geo"]), int(d["anio"])))
    return out


def _bench_mundo(notas: list[str]) -> list[dict[str, Any]]:
    spec = [
        ("wb_arrivals.csv", "arrivals", "wb_arrivals"),
        ("wb_departures.csv", "value", "wb_departures"),
        ("wb_receipts.csv", "value", "wb_receipts"),
    ]
    out: list[dict[str, Any]] = []
    for fname, vcol, ds in spec:
        rows = _records(fname)
        if rows is None:
            notas.append(f"benchmark_mundo: {fname} ausente o vacio, sub-bloque omitido")
            continue
        if not {"countryiso3code", "country", "year", vcol}.issubset(rows[0].keys()):
            notas.append(f"benchmark_mundo: {fname} sin columnas esperadas, sub-bloque omitido")
            continue
        for r in rows:
            v = _num(r.get(vcol))
            if v is None:
                continue
            try:
                anio = int(str(r.get("year", "")).strip()[:4])
            except ValueError:
                continue
            out.append({"iso3": str(r.get("countryiso3code", "")).strip(),
                        "pais": str(r.get("country", "")).strip(),
                        "anio": anio, "valor": v,
                        "indicador": str(r.get("indicator", "")).strip(),
                        "dataset": ds})
    if not out:
        notas.append("benchmark_mundo: sin filas validas, bloque omitido")
    out.sort(key=lambda d: (str(d["dataset"]), str(d["iso3"]), int(d["anio"])))
    return out


def _wikimedia(notas: list[str]) -> list[dict[str, Any]]:
    rows = _records("wikimedia_views.csv")
    if rows is None:
        notas.append("wikimedia: wikimedia_views.csv ausente o vacio, bloque omitido")
        return []
    if not {"timestamp", "views"}.issubset(rows[0].keys()):
        notas.append("wikimedia: columnas esperadas ausentes, bloque omitido")
        return []
    acc: dict[str, float] = {}
    for r in rows:
        ts = _per(str(r.get("timestamp", "").strip()))
        v = _num(r.get("views"))
        if not ts or v is None:
            continue
        acc[ts] = acc.get(ts, 0.0) + v
    if not acc:
        notas.append("wikimedia: sin filas validas, bloque omitido")
        return []
    return [{"periodo": p, "views": int(v)} for p, v in sorted(acc.items())]


def _travel(notas: list[str]) -> list[dict[str, Any]]:
    rows = _records("medata_travel_metrics.csv")
    if rows is None:
        notas.append("travel_metrics: medata_travel_metrics.csv ausente o vacio, bloque omitido")
        return []
    return [dict(r) for r in rows]


def _skips() -> list[str]:
    """SKIP honesto: fuentes vacias, solo-header o muertas. Nunca tumba."""
    skips: list[str] = []
    checks = {
        "gastronomia_osm_med.csv": "vacia",
        "emisores_contexto.csv": "solo header",
        "migrantes_co.csv": "fuente muerta",
    }
    for fname, motivo_base in checks.items():
        p = RAW_DIR / fname
        if not p.exists() or p.stat().st_size == 0:
            skips.append(f"{fname}: ausente o vacio ({motivo_base})")
            continue
        rows = _records(fname)
        if not rows:
            skips.append(f"{fname}: sin filas de datos ({motivo_base})")
        else:
            skips.append(f"{fname}: {len(rows)} filas pero fuera de contrato ({motivo_base})")
    return skips


def main() -> int:
    notas: list[str] = []
    try:
        oferta = _oferta(notas)
        operaciones = _operaciones(notas)
        terrestre = _terrestre(notas)
        metro = _metro(notas)
        trm = _trm(notas)
        costos = _costos(notas)
        bench_eu = _bench_eu(notas)
        bench_mundo = _bench_mundo(notas)
        wiki = _wikimedia(notas)
        travel = _travel(notas)
        skips = _skips()
        # opensky_states.csv: snapshot puntual, sin serie temporal
        open_rows = _records("opensky_states.csv")
        if open_rows is not None:
            notas.append(
                "opensky: opensky_states.csv trae snapshot puntual "
                f"({len(open_rows)} estados), sin serie temporal; no incluido en output"
            )
        else:
            notas.append("opensky: opensky_states.csv ausente o vacio, bloque omitido")
    except Exception as e:  # jamas tumbar: degradar a skip
        payload: dict[str, Any] = {
            "id": "bureau-conectividad-bench",
            "generado": GENERADO,
            "ventana": RAW_DIR.name,
            "fuente": FUENTE,
            "estado": "skip",
            "motivo": f"excepcion no controlada: {e}",
            "skips": _skips(),
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK {OUT} estado=skip motivo={e}")
        return 0

    extremos: list[str] = []
    extremos += [str(b["periodo"]) for b in operaciones]
    extremos += [str(b["periodo"]) for b in terrestre]
    extremos += [str(b["periodo"]) for b in metro]
    extremos += [str(b["periodo"]) for b in wiki]
    for d in trm:
        m = _YEAR_RE.search(str(d.get("date", "")))
        if m:
            extremos.append(m.group(0))
    extremos += [str(b["anio"]) for b in bench_eu + bench_mundo]
    ventana = f"{min(extremos)}..{max(extremos)}" if extremos else RAW_DIR.name

    nucleo = bool(
        oferta["top_rutas"] or operaciones or terrestre or metro or trm
        or costos or bench_eu or bench_mundo or wiki or travel
    )
    payload = {
        "id": "bureau-conectividad-bench",
        "generado": GENERADO,
        "ventana": ventana,
        "fuente": FUENTE,
        "oferta_aerea": oferta,
        "operaciones_serie": operaciones,
        "terrestre_serie": terrestre,
        "metro_serie": metro,
        "trm_serie": trm,
        "costos_destino": costos,
        "benchmark_eu": bench_eu,
        "benchmark_mundo": bench_mundo,
        "wikimedia_serie": wiki,
        "travel_metrics": travel,
        "skips": skips,
        "estado": "ok" if nucleo else "skip",
    }
    if notas:
        payload["notas"] = notas
    if not nucleo:
        payload["motivo"] = "; ".join(notas) if notas else "sin datos en RAW"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {OUT} estado={payload['estado']} "
          f"rutas={len(oferta['top_rutas'])} ops={len(operaciones)} "
          f"terr={len(terrestre)} metro={len(metro)} trm={len(trm)} "
          f"costos={len(costos)} eu={len(bench_eu)} mundo={len(bench_mundo)} "
          f"wiki={len(wiki)} travel={len(travel)} skips={len(skips)}")
    for n in notas:
        print(f"NOTA: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
