"""Amadeus (legado): ofertas aereas MDE-origenes + hoteles MDE.

Self-Service fue dado de baja el 17-jul-2026 (solo queda Enterprise con
contrato): sin keys validas hace SKIP. Reemplazo activo: FlightPowers.
Auth OAuth2 client_credentials con AMADEUS_KEY + AMADEUS_SECRET
(solo Enterprise).
Base por defecto test.api.amadeus.com; produccion opcional con
AMADEUS_BASE_URL (alias legacy AMED_US_BASE_URL) = https://api.amadeus.com.
Endpoints minimos utiles para tablero mercados:
  - Flight Cheapest Date Search (v1/shopping/flight-dates): precio por fecha y ruta.
  - Hotel Search (v1/shopping/hotel-offers, best-effort: si el tier no lo
    permite se sigue solo con vuelos).
Sin keys -> SKIP honesto con instrucciones. 401/429/cualquier error ->
save_or_carry desde base.py, jamas levanta.
Guarda data/raw/<hoy>/amadeus_ofertas.csv con columnas
periodo, origen, destino, precio, moneda, fecha_consulta.
"""

import os
from datetime import date, timedelta

import pandas as pd
import requests

from .base import save_or_carry

TEST_BASE = "https://test.api.amadeus.com"
OAUTH_PATH = "/v1/security/oauth2/token"
FLIGHT_DATES_PATH = "/v1/shopping/flight-dates"
HOTEL_OFFERS_PATH = "/v1/shopping/hotel-offers"

# Rutas MDE-origen utiles al tablero mercados (1 llamada c/u, cuota gratis).
ROUTES = [
    ("MDE", "MIA"),
    ("MDE", "MAD"),
    ("MDE", "MEX"),
    ("MDE", "PTY"),
    ("MDE", "BOG"),
]
HOTEL_CITY = "MDE"

COLUMNS = ["periodo", "origen", "destino", "precio", "moneda", "fecha_consulta"]


def base_url() -> str:
    return (
        os.environ.get("AMADEUS_BASE_URL", "")
        or os.environ.get("AMED_US_BASE_URL", "")
        or TEST_BASE
    ).rstrip("/")


def get_token(base: str, key: str, secret: str) -> str | None:
    """OAuth2 client_credentials. 401/429/red -> None (el caller hace SKIP)."""
    try:
        r = requests.post(
            base + OAUTH_PATH,
            data={
                "grant_type": "client_credentials",
                "client_id": key,
                "client_secret": secret,
            },
            timeout=30,
        )
        if r.status_code == 401:
            print("[amadeus][SKIP] 401: revisar AMADEUS_KEY/AMADEUS_SECRET")
            return None
        if r.status_code == 429:
            print("[amadeus][SKIP] 429 rate-limit en token")
            return None
        r.raise_for_status()
        tok = (r.json() or {}).get("access_token", "")
        return tok or None
    except Exception as e:
        print(f"[amadeus][SKIP] token: {e}")
        return None


def parse_flight_dates(
    payload: dict, origen: str, destino: str, hoy: str | None = None
) -> pd.DataFrame:
    recs: list[dict] = []
    hoy = hoy or date.today().isoformat()
    for it in (payload or {}).get("data") or []:
        try:
            price = it.get("price") or {}
            dep = str(it.get("departureDate", ""))
            recs.append(
                {
                    "periodo": dep[:7],
                    "origen": origen,
                    "destino": destino,
                    "precio": float(price.get("total", float("nan"))),
                    "moneda": price.get("currency", ""),
                    "fecha_consulta": hoy,
                }
            )
        except (TypeError, ValueError):
            continue
    df = pd.DataFrame(recs).reindex(columns=COLUMNS)
    return df.dropna(subset=["precio"])


def parse_hotel_offers(
    payload: dict, ciudad: str, hoy: str | None = None
) -> pd.DataFrame:
    recs: list[dict] = []
    hoy = hoy or date.today().isoformat()
    for item in (payload or {}).get("data") or []:
        hotel = item.get("hotel") or {}
        for off in item.get("offers") or [{}]:
            try:
                price = off.get("price") or {}
                ci = str(off.get("checkInDate", ""))
                recs.append(
                    {
                        "periodo": ci[:7] or hoy[:7],
                        "origen": ciudad,
                        "destino": f"HOTEL-{hotel.get('hotelId', ciudad)}",
                        "precio": float(price.get("total", float("nan"))),
                        "moneda": price.get("currency", ""),
                        "fecha_consulta": hoy,
                    }
                )
            except (TypeError, ValueError):
                continue
    df = pd.DataFrame(recs).reindex(columns=COLUMNS)
    return df.dropna(subset=["precio"])


def _get(base: str, token: str, path: str, params: dict) -> dict | None:
    try:
        r = requests.get(
            base + path,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=40,
        )
        if r.status_code in (401, 429):
            print(f"[amadeus][WARN] HTTP {r.status_code} en {path}")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[amadeus][WARN] {path}: {e}")
        return None


def run() -> bool:
    key = os.environ.get("AMADEUS_KEY", "")
    secret = os.environ.get("AMADEUS_SECRET", "")
    if not key or not secret:
        print(
            "[amadeus][SKIP] sin AMADEUS_KEY/AMADEUS_SECRET validas "
            "(Self-Service dado de baja 17-jul-2026; reemplazo activo: "
            "FlightPowers con FLIGHTPOWERS_KEY)"
        )
        return False
    try:
        base = base_url()
        token = get_token(base, key, secret)
        if not token:
            save_or_carry(pd.DataFrame(), "amadeus_ofertas", COLUMNS)
            return False
        hoy = date.today()
        dep_from = (hoy + timedelta(days=7)).isoformat()
        dep_to = (hoy + timedelta(days=67)).isoformat()
        frames: list[pd.DataFrame] = []
        for org, dst in ROUTES:
            payload = _get(
                base,
                token,
                FLIGHT_DATES_PATH,
                {
                    "origin": org,
                    "destination": dst,
                    "departureDate": f"{dep_from},{dep_to}",
                    "oneWay": "true",
                },
            )
            if payload:
                frames.append(parse_flight_dates(payload, org, dst))
        # Hoteles MDE best-effort: si el tier no lo permite, solo vuelos.
        hotel = _get(
            base,
            token,
            HOTEL_OFFERS_PATH,
            {
                "cityCode": HOTEL_CITY,
                "checkInDate": dep_from,
                "checkOutDate": (hoy + timedelta(days=8)).isoformat(),
                "roomQuantity": "1",
                "adults": "1",
            },
        )
        if hotel:
            frames.append(parse_hotel_offers(hotel, HOTEL_CITY))
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        save_or_carry(df, "amadeus_ofertas", COLUMNS)
        print(f"[amadeus] OK ({len(df)} ofertas)")
        return True
    except Exception as e:
        print(f"[amadeus][SKIP] {e}")
        try:
            save_or_carry(pd.DataFrame(), "amadeus_ofertas", COLUMNS)
        except Exception as e:
            print(f"[amadeus][WARN] carry fallido: {e}")
        return False


if __name__ == "__main__":
    run()
