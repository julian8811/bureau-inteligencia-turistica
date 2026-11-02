"""OpenTripMap: POIs turisticos en radio 30 km de Medellin.

GET https://api.opentripmap.com/0.1/en/places/radius
Requiere OPENTRIPMAP_KEY (gratis con signup libre en https://opentripmap.com/).
Sin key -> SKIP honesto. Radio 30 km sobre Medellin (lon -75.59, lat 6.24),
kinds de interes turistico (cultural,historic,natural,tourism).
Guarda data/raw/<hoy>/opentripmap_med.csv. Nunca tumba el daily.
"""
import os
from datetime import date

import pandas as pd
import requests

from .base import save_or_carry

RADIUS_URL = "https://api.opentripmap.com/0.1/en/places/radius"
LON = -75.59  # Medellin
LAT = 6.24
RADIUS_M = 30000
KINDS = "cultural,historic,natural,tourism"

COLUMNS = ["periodo", "nombre", "kinds", "lon", "lat", "fecha_consulta"]


def _point_lon_lat(place: dict) -> tuple:
    pt = place.get("point") or {}
    if isinstance(pt, dict) and ("lon" in pt or "lat" in pt):
        return pt.get("lon"), pt.get("lat")
    geom = place.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if len(coords) >= 2:
        return coords[0], coords[1]
    return None, None


def parse_places(payload: list | dict, hoy: str | None = None) -> pd.DataFrame:
    """Lista del endpoint radius (o FeatureCollection) -> DataFrame con fecha_consulta."""
    hoy = hoy or date.today().isoformat()
    if isinstance(payload, dict):
        feats = payload.get("features")
        if isinstance(feats, list):
            payload = [f if isinstance(f, dict) and "point" in f else
                       {"name": ((f.get("properties") or {}).get("name", "") if isinstance(f, dict) else ""),
                        "kinds": ((f.get("properties") or {}).get("kinds", "") if isinstance(f, dict) else ""),
                        "geometry": (f.get("geometry") or {} if isinstance(f, dict) else {})}
                       for f in feats]
        else:
            for key in ("results", "data", "places", "geoname"):
                val = payload.get(key)
                if isinstance(val, list):
                    payload = val
                    break
            else:
                payload = [payload] if payload else []
    rows = [r for r in (payload or []) if isinstance(r, dict)]
    recs: list[dict] = []
    for r in rows:
        lon, lat = _point_lon_lat(r)
        recs.append({"periodo": hoy[:7], "nombre": r.get("name", ""),
                     "kinds": r.get("kinds", ""), "lon": lon, "lat": lat,
                     "fecha_consulta": hoy})
    return pd.DataFrame(recs).reindex(columns=COLUMNS)


def run() -> bool:
    key = os.environ.get("OPENTRIPMAP_KEY", "")
    if not key:
        print("[opentripmap][SKIP] sin OPENTRIPMAP_KEY -> skip "
              "(gratis con signup libre en https://opentripmap.com/)")
        return False
    try:
        r = requests.get(RADIUS_URL, params={
            "radius": str(RADIUS_M), "lon": str(LON), "lat": str(LAT),
            "kinds": KINDS, "format": "json", "limit": "500", "apikey": key,
        }, headers={"apikey": key}, timeout=40)
        if r.status_code != 200:
            print(f"[opentripmap][SKIP] HTTP {r.status_code}")
            return False
        df = parse_places(r.json())
        save_or_carry(df, "opentripmap_med", COLUMNS)
        if df.empty:
            print("[opentripmap][SKIP] sin POIs -> carry")
            return False
        print(f"[opentripmap] OK ({len(df)} POIs)")
        return True
    except Exception as e:
        print(f"[opentripmap][SKIP] {e}")
        return False


if __name__ == "__main__":
    run()
