"""Clima y aire -> tableros-bureau (T3, S3-S5).

Lee RAW de data/raw/<FECHA>/ y publica export/tableros_bureau/clima_aire_2025_2026.json.
Solo stdlib + pandas. UTF-8. Defensivo: archivo ausente o vacio -> bloque
omitido con nota + estado ok si hay nucleo, skip si no hay nada; exit 0, nunca tumba.
No toca /tmp/tableros-bureau ni ningun otro repo.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW_DIR = BASE / "data" / "raw" / "2026-11-02"
OUT = BASE / "export" / "tableros_bureau" / "clima_aire_2025_2026.json"
FUENTE = "ETL Bureau, IDEAM + Open-Meteo + aire_med"
GENERADO = date.today().isoformat()


def _load(name: str) -> pd.DataFrame | None:
    p = RAW_DIR / name
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    if df.empty:
        return None
    return df


def _lluvia(notas: list[str]) -> list[dict]:
    df = _load("ideam_lluvia_med.csv")
    if df is None:
        notas.append("lluvia: ideam_lluvia_med.csv ausente o vacio, bloque omitido")
        return []
    need = {"codigoestacion", "fechaobservacion", "valorobservado"}
    if not need.issubset(df.columns):
        notas.append("lluvia: columnas esperadas ausentes, bloque omitido")
        return []
    df = df.dropna(subset=["fechaobservacion", "valorobservado"])
    if df.empty:
        notas.append("lluvia: sin filas validas, bloque omitido")
        return []
    df["periodo"] = df["fechaobservacion"].astype(str).str.slice(0, 7)
    out = []
    for periodo, g in sorted(df.groupby("periodo").groups.items()):
        sub = df.loc[g]
        out.append(
            {
                "periodo": periodo,
                "mm_prom": round(float(sub["valorobservado"].mean()), 3),
                "n_estaciones": int(sub["codigoestacion"].nunique()),
            }
        )
    return out


def _pm25(notas: list[str]) -> list[dict]:
    df = _load("aire_med.csv")
    if df is None:
        notas.append("pm25: aire_med.csv ausente o vacio, bloque omitido")
        return []
    if not {"datetime", "pm2_5"}.issubset(df.columns):
        notas.append("pm25: columnas esperadas ausentes, bloque omitido")
        return []
    df = df.dropna(subset=["datetime", "pm2_5"])
    return [{"fecha": str(r[0]), "pm2_5": float(r[1])} for r in df.itertuples(index=False)]


def _pronostico(notas: list[str]) -> list[dict]:
    df = _load("openmeteo_ensemble.csv")
    if df is None:
        notas.append("pronostico: openmeteo_ensemble.csv ausente o vacio, bloque omitido")
        return []
    need = {"date", "tmax_mean", "prec_mean", "prec_p10", "prec_p90"}
    if not need.issubset(df.columns):
        notas.append("pronostico: columnas esperadas ausentes, bloque omitido")
        return []
    out = []
    for row in df.to_dict(orient="records"):
        out.append(
            {
                "date": str(row["date"]),
                "tmax_mean": round(float(row["tmax_mean"]), 3),
                "prec_mean": round(float(row["prec_mean"]), 3),
                "prec_p10": round(float(row["prec_p10"]), 3),
                "prec_p90": round(float(row["prec_p90"]), 3),
            }
        )
    return out


def main() -> int:
    notas: list[str] = []
    lluvia = _lluvia(notas)
    pm25 = _pm25(notas)
    pron = _pronostico(notas)

    periodos = [b["periodo"] for b in lluvia]
    fechas = [b["date"] for b in pron]
    extremos = periodos + fechas + [b["fecha"][:10] for b in pm25 if b["fecha"]]
    ventana = f"{min(extremos)}..{max(extremos)}" if extremos else RAW_DIR.name

    nucleo = bool(lluvia or pm25 or pron)
    payload: dict = {
        "id": "bureau-clima",
        "generado": GENERADO,
        "ventana": ventana,
        "fuente": FUENTE,
        "lluvia_mensual": lluvia,
        "pm25_serie": pm25,
        "pronostico": pron,
        "estado": "ok" if nucleo else "skip",
    }
    if notas:
        payload["notas"] = notas
    if not nucleo:
        payload["motivo"] = "; ".join(notas) if notas else "sin datos en RAW"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {OUT} estado={payload['estado']} "
          f"lluvia={len(lluvia)} pm25={len(pm25)} pron={len(pron)}")
    for n in notas:
        print(f"NOTA: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
