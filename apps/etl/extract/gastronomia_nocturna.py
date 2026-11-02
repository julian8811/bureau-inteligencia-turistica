"""Oferta nocturna/gastronómica Medellín (vacacional + social MICE).
- OSM Overpass: amenity restaurante/bar/café/pub/nightclub en bbox Medellín (sin key).
  Si la red bloquea Overpass -> SKIP honesto con carry-forward.
- Alumbrado: Socrata datasets queryables de alumbrado en Antioquia (proxy noche).
Límites pequeños (máx 3000 nodos, timeout corto). Nunca tumba el daily.
Barrido 01-nov: Overpass con timeouts/406 (OSM muerto) mientras alumbrados
trae 1000 filas -> OSM a intento único corto (15s, primer host, sin reintentos
largos); alumbrados intacto.
"""
from pathlib import Path

import pandas as pd
import requests

from .base import UA, paginate_socrata, save_or_carry

OVERPASS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
# bbox Medellín: sur,oeste,norte,este
BBOX = "6.05,-75.65,6.45,-75.40"
ALUMBRADO_CANDIDATOS = ["5upz-u2vi"]  # parque lumínico Sabaneta (Valle de Aburrá)


OSM_TIMEOUT_S = 15  # intento unico corto (barrido 01-nov: OSM muerto)


def _overpass_query() -> dict:
    # Intento UNICO y corto: solo el primer host, 15s. Sin reintentos largos:
    # si OSM esta caido, SKIP honesto con carry y el daily sigue (alumbrados
    # trae el dato de noche igual).
    q = (
        f"[out:json][timeout:15];("
        f'node["amenity"~"restaurant|bar|cafe|fast_food|pub|nightclub"]({BBOX});'
        f'way["amenity"~"restaurant|bar|cafe|fast_food|pub|nightclub"]({BBOX});'
        f");out center 3000;"
    )
    host = OVERPASS[0]
    try:
        r = requests.post(host, data={"data": q}, headers=UA, timeout=OSM_TIMEOUT_S)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        last = str(e)[:130]
        print(f"[gastronomia_nocturna][WARN] overpass {host}: {last}")
        raise RuntimeError(f"overpass sin respuesta ({last})") from e


def run_osm_gastronomia() -> Path:
    try:
        data = _overpass_query()
        rows = []
        for el in data.get("elements", [])[:3000]:
            tags = el.get("tags", {})
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            rows.append({
                "tipo": el.get("type"), "id": el.get("id"),
                "lat": lat, "lon": lon,
                "nombre": tags.get("name", ""),
                "amenity": tags.get("amenity", ""),
                "cocina": tags.get("cuisine", ""),
                "horario": tags.get("opening_hours", ""),
            })
        df = pd.DataFrame(rows)
    except Exception as e:
        print(f"[gastronomia_nocturna][WARN] osm: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "gastronomia_osm_med")


def run_alumbrados() -> Path:
    df = pd.DataFrame()
    for did in ALUMBRADO_CANDIDATOS:
        for params in ({"municipio": "Sabaneta"}, {}):
            try:
                cand = paginate_socrata(did, dict(params, **{"$limit": "1000"}),
                                        page_size=1000, max_pages=1)
            except Exception as e:
                print(f"[gastronomia_nocturna][WARN] alumbrado {did}: {str(e)[:130]}")
                continue
            if not cand.empty:
                df = cand
                break
        if not df.empty:
            break
    return save_or_carry(df, "alumbrados_antioquia")


def run() -> list[Path]:
    return [run_osm_gastronomia(), run_alumbrados()]


if __name__ == "__main__":
    run()
