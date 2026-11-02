"""AirportMiles MDE/EOH — aeropuertos del valle (Nuxt payload).

Tematica: conectividad — códigos IATA MDE/EOH para el dashboard Bureau.
Endpoint free sin key: https://airportmiles.com/_payload.json
(sitio Nuxt; si cambia el build-id o el payload no trae MDE/EOH
-> vacío honesto + carry-forward, nunca tumba el daily).
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COLUMNS = ["iata", "nombre", "ciudad", "pais", "lat", "lon", "fuente"]

_WANT = ("MDE", "EOH")
_CITY_HINTS = ("rionegro", "medell", "josé maría córdova", "jose maria cordova",
               "olaya herrera")


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _norm(text) -> str:
    return str(text or "").strip().lower()


def _match(rec: dict) -> dict | None:
    """True si el registro describe MDE o EOH (por IATA o por ciudad/nombre)."""
    blob = " ".join(
        str(rec.get(k) or "") for k in
        ("iata", "code", "nombre", "name", "ciudad", "city", "pais", "country")
    )
    low = _norm(blob)
    codes = {str(rec.get(k) or "").strip().upper() for k in ("iata", "code", "icao")}
    if codes & set(_WANT):
        return rec
    if any(h in low for h in _CITY_HINTS) and ("mde" in low or "eoh" in low or "medell" in low or "rionegro" in low):
        return rec
    if "mde" in low or "eoh" in low:
        return rec
    return None


def _iter_candidates(payload) -> list[dict]:
    """Aplana el payload Nuxt buscando dicts con pinta de aeropuerto."""
    out: list[dict] = []

    def walk(node):
        if isinstance(node, dict):
            keys = {str(k).lower() for k in node}
            if keys & {"iata", "code"} and keys & {"nombre", "name", "ciudad", "city"}:
                out.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload or {})
    return out


def parse_payload(payload) -> pd.DataFrame:
    """Filtra MDE/EOH (o Rionegro/Medellín) del payload Nuxt."""
    try:
        recs = []
        for rec in _iter_candidates(payload):
            if _match(rec) is None:
                continue
            iata = str(rec.get("iata") or rec.get("code") or "").strip().upper()
            if iata not in _WANT:
                continue
            recs.append(
                {
                    "iata": iata,
                    "nombre": rec.get("nombre") or rec.get("name") or "",
                    "ciudad": rec.get("ciudad") or rec.get("city") or "",
                    "pais": rec.get("pais") or rec.get("country") or "Colombia",
                    "lat": rec.get("lat") if rec.get("lat") is not None
                    else rec.get("latitude"),
                    "lon": rec.get("lon") if rec.get("lon") is not None
                    else rec.get("longitude"),
                    "fuente": "airportmiles",
                }
            )
        # de-duplicar por IATA
        seen: dict[str, dict] = {}
        for r in recs:
            seen.setdefault(r["iata"], r)
        df = pd.DataFrame(list(seen.values())).reindex(columns=COLUMNS)
        print(f"[extract] airportmiles parse: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] airportmiles parse: {e}")
        return _empty()


def run_mde() -> pd.DataFrame:
    """run() individual: GET al payload Nuxt y filtra MDE/EOH."""
    try:
        r = requests.get(
            "https://airportmiles.com/_payload.json",
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        df = parse_payload(r.json())
        print(f"[extract] airportmiles_mde: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] airportmiles_mde: {e}")
        return _empty()


def run():
    """run() agregador: guarda data/raw/<hoy>/airportmiles_mde.csv, nunca levanta."""
    try:
        df = run_mde()
    except Exception as e:
        print(f"[extract][WARN] airportmiles_mde agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "airportmiles_mde", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] airportmiles_mde save: {e}")
        return []


if __name__ == "__main__":
    run()
