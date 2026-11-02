"""TieredTravel Medellin — costos tiers + conteos hoteles/atracciones.

Tematica: costos de destino para dashboard Bureau (derrama y pricing MICE/vacacional).
Endpoints free sin key (auth opcional):
  GET https://tieredtravel.com/api/v1/destinations
  GET https://tieredtravel.com/api/v1/hotels
  GET https://tieredtravel.com/api/v1/attractions
Filtra slug/nombre que contenga medellin (case-insensitive, sin acentos);
si no hay match -> guarda conteo global + fila medellin vacia con ceros
(nunca vacio sin carry). Nunca tumba el daily.
"""

import unicodedata

import pandas as pd
import requests

from .base import UA, save_or_carry

DESTINATIONS_URL = "https://tieredtravel.com/api/v1/destinations"
HOTELS_URL = "https://tieredtravel.com/api/v1/hotels"
ATTRACTIONS_URL = "https://tieredtravel.com/api/v1/attractions"

COLUMNS = ["slug", "nombre", "pais", "costo_budget", "costo_mid", "costo_luxury",
           "n_hoteles", "n_atracciones"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _norm(text) -> str:
    """Minusculas sin acentos para matchear medellin/Medellín."""
    s = str(text or "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _get(item: dict, *keys, default=None):
    for k in keys:
        if isinstance(item, dict) and item.get(k) is not None:
            return item.get(k)
    return default


def _is_medellin(item: dict) -> bool:
    hay = " ".join(str(_get(item, k, default="") or "") for k in
                   ("slug", "name", "nombre", "destination", "city", "id", "code"))
    return "medellin" in _norm(hay)


def _as_list(payload) -> list:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [i for i in payload if isinstance(i, dict)]
    if isinstance(payload, dict):
        for k in ("destinations", "data", "results", "hotels", "attractions", "items"):
            v = payload.get(k)
            if isinstance(v, list):
                return [i for i in v if isinstance(i, dict)]
        # dict suelto con pinta de destino -> 1 item
        if _get(payload, "slug", "name", "nombre", default=None) is not None:
            return [payload]
    return []


def _cost(item: dict, tier: str):
    """Busca el tier en claves planas y en dicts anidados costs/cost/prices."""
    tier_keys = {
        "budget": ("costo_budget", "cost_budget", "budget", "budget_cost", "costBudget",
                   "low", "economy", "backpacker"),
        "mid": ("costo_mid", "cost_mid", "mid", "midrange", "mid_range", "midRange",
                "medium", "standard", "comfort"),
        "luxury": ("costo_luxury", "cost_luxury", "luxury", "high", "premium", "deluxe"),
    }
    v = _get(item, *tier_keys[tier], default=None)
    if v is not None:
        return v
    for nk in ("costs", "cost", "prices", "average_costs", "averageCosts", "price"):
        nested = item.get(nk) if isinstance(item, dict) else None
        if isinstance(nested, dict):
            for k, val in nested.items():
                if tier in _norm(k) or (tier == "mid" and _norm(k) in ("medium", "standard", "comfort", "midrange", "mid_range")):
                    return val
                if tier == "budget" and _norm(k) in ("low", "economy", "backpacker", "budget"):
                    return val
                if tier == "luxury" and _norm(k) in ("high", "premium", "deluxe", "luxury"):
                    return val
    return 0


def parse_destinations(payload, n_hoteles: int = 0, n_atracciones: int = 0) -> pd.DataFrame:
    """Parsea payload destinations -> 1 fila por match medellin.

    Sin match: 1 fila medellin vacia con ceros + conteos globales
    (nunca vacio sin carry).
    """
    try:
        items = _as_list(payload)
        matches = [i for i in items if _is_medellin(i)]
        recs = []
        for i in matches:
            recs.append({
                "slug": str(_get(i, "slug", "id", "code", default="") or ""),
                "nombre": str(_get(i, "name", "nombre", "destination", "city", default="") or ""),
                "pais": str(_get(i, "country", "pais", "country_name", default="") or ""),
                "costo_budget": _cost(i, "budget"),
                "costo_mid": _cost(i, "mid"),
                "costo_luxury": _cost(i, "luxury"),
                "n_hoteles": n_hoteles,
                "n_atracciones": n_atracciones,
            })
        if not recs:
            recs.append({
                "slug": "medellin",
                "nombre": "Medellín",
                "pais": "",
                "costo_budget": 0,
                "costo_mid": 0,
                "costo_luxury": 0,
                "n_hoteles": n_hoteles,
                "n_atracciones": n_atracciones,
            })
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        print(f"[extract] tieredtravel parse: {len(items)} destinos, {len(matches)} match medellin")
        return df
    except Exception as e:
        print(f"[extract][WARN] tieredtravel parse: {e}")
        return _empty()


def _fetch(url: str):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def run():
    """run() agregador: destinations + conteos hotels/attractions, guarda csv con carry."""
    try:
        try:
            dest_payload = _fetch(DESTINATIONS_URL)
        except Exception as e:
            print(f"[extract][WARN] tieredtravel destinations: {e}")
            dest_payload = None
        try:
            n_hoteles = len(_as_list(_fetch(HOTELS_URL)))
        except Exception as e:
            print(f"[extract][WARN] tieredtravel hotels: {e}")
            n_hoteles = 0
        try:
            n_atracciones = len(_as_list(_fetch(ATTRACTIONS_URL)))
        except Exception as e:
            print(f"[extract][WARN] tieredtravel attractions: {e}")
            n_atracciones = 0
        df = parse_destinations(dest_payload, n_hoteles, n_atracciones)
        print(f"[extract] tieredtravel_med: {len(df)} filas "
              f"(hoteles={n_hoteles}, atracciones={n_atracciones})")
    except Exception as e:
        print(f"[extract][WARN] tieredtravel agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "tieredtravel_med", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] tieredtravel save: {e}")
        return []


if __name__ == "__main__":
    run()
