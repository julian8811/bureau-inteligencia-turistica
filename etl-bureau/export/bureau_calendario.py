"""Calendario y contexto (feriados CO + estaciones IDEAM) para tableros-bureau.

Lee RAW de data/raw/<ultimo>/ y publica
export/tableros_bureau/calendario_contexto_2025_2026.json.
Solo stdlib + pandas. Lectura defensiva: si falta un insumo, el bloque
se omite con nota; si no hay núcleo, estado=skip. Jamas tumba (exit 0).
"""
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RAW_DIR = sorted((BASE / "data" / "raw").glob("20*"))[-1]
OUT = BASE / "export" / "tableros_bureau" / "calendario_contexto_2025_2026.json"
GENERADO = RAW_DIR.name
FUENTE = "ETL Bureau, festivos CO + IDEAM"


def _read(name):
    p = RAW_DIR / name
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        import pandas as pd
        df = pd.read_csv(p, dtype=str).fillna("")
        if df.empty:
            return None
        return [dict(r) for r in df.to_dict(orient="records")]
    except Exception:
        return None


def main() -> int:
    notas: list[str] = []
    try:
        fest = _read("festivos_co.csv")
        est = _read("ideam_estaciones_med.csv")
        if fest is None:
            notas.append("festivos: festivos_co.csv ausente o vacio, bloque omitido")
            feriados = []
        else:
            feriados = sorted(
                ({"date": str(r.get("date", "")).strip(),
                  "nombre": str(r.get("localName", "") or r.get("name", "")).strip()}
                 for r in fest if str(r.get("date", "")).strip()),
                key=lambda d: d["date"],
            )
            if not feriados:
                notas.append("festivos: sin filas validas, bloque omitido")
        if est is None:
            notas.append("estaciones: ideam_estaciones_med.csv ausente o vacio, bloque omitido")
            estaciones = {}
        else:
            por_estado = Counter(str(r.get("estado", "")).strip() or "?" for r in est)
            por_cat = Counter(str(r.get("categoria", "")).strip() or "?" for r in est)
            por_mun = Counter(str(r.get("municipio", "")).strip() or "?" for r in est)
            con_coords = sum(1 for r in est if str(r.get("latitud", "")).strip()
                             and str(r.get("longitud", "")).strip())
            estaciones = {
                "total": len(est),
                "por_estado": dict(por_estado),
                "por_categoria": dict(por_cat.most_common(10)),
                "top_municipios": [{"municipio": m, "n": n}
                                   for m, n in por_mun.most_common(10)],
                "con_coordenadas": con_coords,
            }
    except Exception as e:  # jamas tumbar
        payload = {"id": "bureau-calendario", "generado": GENERADO,
                   "ventana": RAW_DIR.name, "fuente": FUENTE,
                   "estado": "skip", "motivo": f"excepcion no controlada: {e}"}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK {OUT} estado=skip motivo={e}")
        return 0

    nucleo = bool(feriados or estaciones)
    anios = sorted({d["date"][:4] for d in feriados if len(d["date"]) >= 4})
    payload = {
        "id": "bureau-calendario",
        "generado": GENERADO,
        "ventana": "-".join(anios) if anios else RAW_DIR.name,
        "fuente": FUENTE,
        "festivos": feriados,
        "estaciones": estaciones,
        "estado": "ok" if nucleo else "skip",
    }
    if notas:
        payload["notas"] = notas
    if not nucleo:
        payload["motivo"] = "; ".join(notas) if notas else "sin datos en RAW"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {OUT} estado={payload['estado']} festivos={len(feriados)} "
          f"estaciones={estaciones.get('total', 0) if isinstance(estaciones, dict) else 0}")
    for n in notas:
        print(f"NOTA: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
