"""AeroDataBox: estado de vuelos MDE (SKRG) / EOH (SKMD) via RapidAPI.

Auth con la misma RapidAPI key de FlightPowers (reusar FLIGHTPOWERS_KEY),
o AERODATABOX_KEY dedicada si existe; header x-rapidapi-key.
Alta: RapidAPI hub 'AeroDataBox' (plan Basic con cuota gratis mensual).
Endpoints (docs RapidAPI AeroDataBox):
  - GET https://aerodatabox.p.rapidapi.com/airports/icao/{icao}/delays
    (alternativa: /flights/airports/icao/{icao} si el plan no incluye delays).
Sin key -> SKIP honesto con instrucciones. 401/429/cualquier error ->
save_or_carry desde base.py, jamás levanta.
1 call por aeropuerto por corrida (SKRG + SKMD).
Guarda data/raw/<hoy>/aerodatabox_mde.csv con columnas
aeropuerto, vuelo, origen, destino, estado, programado, retraso_min, fecha_consulta.
"""

import os
from datetime import date

import pandas as pd
import requests

from .base import save_or_carry

RAPID_HOST = "aerodatabox.p.rapidapi.com"
API_BASE = f"https://{RAPID_HOST}"

# ICAO: SKRG = MDE José María Córdova, SKMD = EOH Olaya Herrera. 1 call c/u.
AIRPORTS = ("SKRG", "SKMD")
OUT_NAME = "aerodatabox_mde"

COLUMNS = ["aeropuerto", "vuelo", "origen", "destino", "estado",
           "programado", "retraso_min", "fecha_consulta"]


def _key() -> str:
    return os.environ.get("AERODATABOX_KEY", "") or os.environ.get("FLIGHTPOWERS_KEY", "")


def _headers(key: str) -> dict:
    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": RAPID_HOST,
        "Accept": "application/json",
    }


def _as_list(payload: object) -> list:
    """El API envuelve en departures/arrivals/flights/items."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("departures", "arrivals", "flights", "items", "data", "results"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for sub in ("departures", "arrivals", "flights", "items"):
                    inner = v.get(sub)
                    if isinstance(inner, list):
                        return inner
    return []


def _nested(d: dict, *keys: str, default: str = "") -> str:
    cur: object = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return str(cur) if cur is not None else default


def parse_status(payload: dict | list, aeropuerto: str, hoy: str | None = None) -> pd.DataFrame:
    recs: list[dict] = []
    hoy = hoy or date.today().isoformat()
    for it in _as_list(payload):
        if not isinstance(it, dict):
            continue
        vuelo = str(it.get("number") or it.get("flightNumber") or it.get("flight_number")
                      or it.get("callsign") or "")
        estado = str(it.get("status") or it.get("flightStatus") or "")
        programado = (_nested(it, "departure", "scheduledTimeUtc")
                      or _nested(it, "departure", "scheduledTimeLocal")
                      or str(it.get("scheduledTimeUtc") or it.get("scheduled") or ""))
        destino = (_nested(it, "arrival", "airport", "iata")
                   or str(it.get("destination") or it.get("dest") or ""))
        origen = (_nested(it, "departure", "airport", "iata")
                  or str(it.get("origin") or aeropuerto))
        try:
            retraso = it.get("delayMinutes", it.get("delay_minutes", it.get("delay", 0)))
            retraso_min = int(float(retraso or 0))
        except (TypeError, ValueError):
            retraso_min = 0
        recs.append({
            "aeropuerto": aeropuerto,
            "vuelo": vuelo,
            "origen": origen or aeropuerto,
            "destino": destino,
            "estado": estado,
            "programado": programado,
            "retraso_min": retraso_min,
            "fecha_consulta": hoy,
        })
    df = pd.DataFrame(recs).reindex(columns=COLUMNS)
    return df


def _get_delays(key: str, icao: str) -> dict | list | None:
    """GET defensivo: 401/429/cualquier error -> None (el caller hace SKIP/carry)."""
    try:
        r = requests.get(
            f"{API_BASE}/airports/icao/{icao}/delays",
            headers=_headers(key),
            timeout=40,
        )
        if r.status_code in (401, 403, 429):
            print(f"[aerodatabox][WARN] HTTP {r.status_code} delays {icao}")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[aerodatabox][WARN] delays {icao}: {e}")
        return None


def run() -> bool:
    key = _key()
    if not key:
        print(
            "[aerodatabox][SKIP] sin AERODATABOX_KEY ni FLIGHTPOWERS_KEY -> "
            "alta gratis en RapidAPI hub 'AeroDataBox' (plan Basic con cuota "
            "gratis mensual; misma RapidAPI key de FlightPowers sirve) y "
            "exportar la key en ~/.bureau_backend_env"
        )
        return False
    try:
        frames: list[pd.DataFrame] = []
        for icao in AIRPORTS:  # 1 call por aeropuerto
            payload = _get_delays(key, icao)
            if payload is not None:
                df = parse_status(payload, icao)
                if not df.empty:
                    frames.append(df)
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        save_or_carry(df, OUT_NAME, COLUMNS)
        if df.empty:
            print("[aerodatabox][SKIP] sin vuelos nuevos -> verificar key/cuota RapidAPI")
            return False
        print(f"[aerodatabox] OK ({len(df)} vuelos MDE/EOH)")
        return True
    except Exception as e:
        print(f"[aerodatabox][SKIP] {e}")
        try:
            save_or_carry(pd.DataFrame(), OUT_NAME, COLUMNS)
        except Exception as e:
            print(f"[aerodatabox][WARN] carry fallido: {e}")
        return False


if __name__ == "__main__":
    run()
