"""Ticketmaster Discovery API: agenda de eventos/conciertos en Medellín.

GET https://app.ticketmaster.com/discovery/v2/events.json
Requiere TICKETMASTER_KEY (gratis en developer.ticketmaster.com).
Sin key -> SKIP honesto. Radio 60 km sobre Medellín, país CO,
categorías música/artes/teatro. Nunca tumba el daily.
"""
import os
from datetime import date

import pandas as pd
import requests

from .base import save_or_carry

DISCOVERY = "https://app.ticketmaster.com/discovery/v2/events.json"
LATLONG = "6.2442,-75.5812"  # Medellín

COLUMNS = ["periodo", "fecha", "nombre", "recinto", "ciudad",
           "categoria", "url", "fecha_consulta"]


def _ciudad(v: dict) -> str:
    try:
        return (v.get("_embedded") or {}).get("venues", [{}])[0].get("city", {}).get("name", "")
    except Exception:
        return ""


def _recinto(v: dict) -> str:
    try:
        return (v.get("_embedded") or {}).get("venues", [{}])[0].get("name", "")
    except Exception:
        return ""


def _categoria(v: dict) -> str:
    try:
        return (v.get("classifications") or [{}])[0].get("segment", {}).get("name", "")
    except Exception:
        return ""


def parse_events(payload: dict) -> pd.DataFrame:
    recs: list[dict] = []
    hoy = date.today().isoformat()
    events = ((payload or {}).get("_embedded") or {}).get("events") or []
    for ev in events:
        fecha = ((ev.get("dates") or {}).get("start") or {}).get("localDate", "")
        recs.append({"periodo": str(fecha)[:7], "fecha": fecha,
                     "nombre": ev.get("name", ""), "recinto": _recinto(ev),
                     "ciudad": _ciudad(ev), "categoria": _categoria(ev),
                     "url": ev.get("url", ""), "fecha_consulta": hoy})
    return pd.DataFrame(recs).reindex(columns=COLUMNS)


def run() -> bool:
    key = os.environ.get("TICKETMASTER_KEY", "")
    if not key:
        print("[ticketmaster][SKIP] sin TICKETMASTER_KEY -> skip")
        return False
    try:
        r = requests.get(DISCOVERY, params={
            "apikey": key, "latlong": LATLONG, "radius": "60", "unit": "km",
            "countryCode": "CO", "size": "100", "sort": "date,asc", "locale": "es",
        }, timeout=40)
        if r.status_code != 200:
            print(f"[ticketmaster][SKIP] HTTP {r.status_code}")
            return False
        df = parse_events(r.json())
        save_or_carry(df, "ticketmaster_eventos", COLUMNS)
        print(f"[ticketmaster] OK ({len(df)} eventos)")
        return True
    except Exception as e:
        print(f"[ticketmaster][SKIP] {e}")
        return False


if __name__ == "__main__":
    run()
