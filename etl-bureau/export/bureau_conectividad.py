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

Fuentes descontinuadas (retiradas 2026-11-02, ver `retiradas` en el
payload): flota Aerocivil (solo ene-feb 2020), terminales (a 2023-12),
metro (a 2020-12), travel_metrics (a 2023-09), tarifa por zona
(a 2023-03), costos TieredTravel (ceros), opensky (snapshot sin serie).
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
FUENTE = "ETL Bureau, Aerocivil/Eurostat/WB/Wikimedia"
GENERADO = date.today().isoformat()

_YEAR_RE = re.compile(r"(?:19|20)\d{2}")

RETIRADAS = [
    "aerocivil_flota.csv: solo ene-feb 2020, sin serie vigente",
    "terminales_med.csv: corta en 2023-12",
    "movilidad_metro_med.csv: corta en 2020-12",
    "medata_travel_metrics.csv: corta en 2023-09",
    "medata_tarifa_zona.csv: corta en 2023-03",
    "tieredtravel_med.csv: una fila de ceros",
    "opensky_states.csv: snapshot puntual, sin serie temporal",
]


def _per(s: str) -> str:
    """Normaliza un periodo a YYYY-MM (raw trae YYYYMM o YYYYMMDDHH)."""
    t = re.sub(r"\D", "", s)
    if len(t) >= 6 and "1900" <= t[:4] <= "2100" and "01" <= t[4:6] <= "12":
        return f"{t[:4]}-{t[4:6]}"
    m = re.fullmatch(r"(\d{4})-(\d{2})(-\d{2})?", s.strip())
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return s.strip()


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


def _trm_fecha(dt: str) -> str:
    """Normaliza fecha TRM/FX a YYYY-MM-DD (raw trae ISO o RFC2822)."""
    s = dt.strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", s)
    if m:
        meses = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                 "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                 "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
        mes = meses.get(m.group(2), "01")
        return f"{m.group(3)}-{mes}-{m.group(1).zfill(2)}"
    return s


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
        operaciones = _operaciones(notas)
        trm = _trm(notas)
        bench_eu = _bench_eu(notas)
        wiki = _wikimedia(notas)
        skips = _skips()
    except Exception as e:  # jamas tumbar: degradar a skip
        payload: dict[str, Any] = {
            "id": "bureau-conectividad-bench",
            "generado": GENERADO,
            "ventana": RAW_DIR.name,
            "fuente": FUENTE,
            "estado": "skip",
            "motivo": f"excepcion no controlada: {e}",
            "skips": _skips(),
            "retiradas": RETIRADAS,
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK {OUT} estado=skip motivo={e}")
        return 0

    cortes = {
        "operaciones": max((b["periodo"] for b in operaciones), default=""),
        "trm": max((_trm_fecha(str(d.get("date", ""))) for d in trm), default=""),
        "benchmark_eu": max((b["anio"] for b in bench_eu), default=0),
        "wikimedia": max((b["periodo"] for b in wiki), default=""),
    }
    extremos = [cortes["operaciones"], cortes["wikimedia"]]
    extremos += [str(b["anio"]) for b in bench_eu]
    ventana = f"{min(extremos)}..{max(extremos)}" if all(extremos) else RAW_DIR.name

    nucleo = bool(operaciones or trm or bench_eu or wiki)
    payload = {
        "id": "bureau-conectividad-bench",
        "generado": GENERADO,
        "ventana": ventana,
        "fuente": FUENTE,
        "operaciones_serie": operaciones,
        "trm_serie": trm,
        "benchmark_eu": bench_eu,
        "wikimedia_serie": wiki,
        "cortes": cortes,
        "skips": skips,
        "retiradas": RETIRADAS,
        "estado": "ok" if nucleo else "skip",
    }
    if notas:
        payload["notas"] = notas
    if not nucleo:
        payload["motivo"] = "; ".join(notas) if notas else "sin datos en RAW"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {OUT} estado={payload['estado']} "
          f"ops={len(operaciones)} trm={len(trm)} "
          f"eu={len(bench_eu)} "
          f"wiki={len(wiki)} skips={len(skips)}")
    for n in notas:
        print(f"NOTA: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
