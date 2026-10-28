"""Gated Amadeus Developers (solo API oficial con key, nunca scraping).

Lee AMADEUS_KEY / AMADEUS_SECRET del entorno.
Sin keys -> SKIP (el daily sigue). Con keys -> deja plantilla de respuesta
en data/raw/<hoy>/amadeus_dev.json para que transform lo absorba.
No hace llamadas reales sin keys para no quemar cuota en cron.
"""
import json
import os
from datetime import date
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def run():
    hoy = date.today().isoformat()
    outdir = RAW / hoy
    outdir.mkdir(parents=True, exist_ok=True)
    key = os.getenv("AMADEUS_KEY", "")
    secret = os.getenv("AMADEUS_SECRET", "")
    has_key = bool(key and secret)
    manual = sorted((RAW / "manual").glob("amadeus*")) if (RAW / "manual").exists() else []
    if not has_key and not manual:
        print("[gated][SKIP] amadeus_dev sin AMADEUS_KEY ni manual/amadeus* -> skip")
        return pd_empty()
    payload = {"fecha": hoy, "origen": "manual" if manual else "api",
               "archivos": [p.name for p in manual]}
    (outdir / "amadeus_dev.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[gated] amadeus_dev -> {outdir / 'amadeus_dev.json'}")
    return payload


def pd_empty():
    try:
        import pandas as pd
        return pd.DataFrame()
    except Exception:
        return None


if __name__ == "__main__":
    run()
