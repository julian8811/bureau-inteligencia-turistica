"""FlightPowers (Google Flights live, reemplazo Amadeus): ofertas oneway MDE-origenes.

Auth con FLIGHTPOWERS_KEY desde entorno (RapidAPI "Google Flights Live API":
https://flightpowers.com/docs; alta en RapidAPI plan BASIC gratis 10 req/mes
sin tarjeta o PRO $10 2500 req/mes; la key de RapidAPI va en el header
x-api-key —también acepta x-rapidapi-key / Authorization Bearer—; exportar en
~/.bureau_backend_env).
Endpoints: POST https://api.flightpowers.com/v1/flights/oneway
(y /roundtrip como alternativa; aquí solo oneway para no quemar cuota).
Sin key -> SKIP honesto con instrucciones. 401/429/cualquier error ->
save_or_carry desde base.py, jamás levanta.
Máx 5 calls por corrida (1 por ruta) para no quemar la cuota (10/mes).
Guarda data/raw/<hoy>/flightpowers_ofertas.csv con columnas
periodo, origen, destino, precio, moneda, fecha_consulta.
Docs: https://flightpowers.com/docs,
https://flightpowers.com/integrations/api/one-way-search.
"""

import os
from datetime import date, timedelta

import pandas as pd
import requests

from .base import save_or_carry

API_BASE = "https://api.flightpowers.com"
ONEWAY_PATH = "/v1/flights/oneway"

# 5 rutas MDE (orígenes top del ETL: USA/MEX/BRA + MAD/PTY). 1 call c/u.
ROUTES = [
    ("MDE", "MIA"),  # USA
    ("MDE", "MEX"),  # MEX
    ("MDE", "GRU"),  # BRA
    ("MDE", "MAD"),  # ESP
    ("MDE", "PTY"),  # PAN
]
MAX_CALLS = 5

COLUMNS = ["periodo", "origen", "destino", "precio", "moneda", "fecha_consulta"]
OUT_NAME = "flightpowers_ofertas"

# Hoteles (T1 S1): misma FLIGHTPOWERS_KEY, cuota BASIC 10/mes compartida con
# vuelos -> máx 2 calls por corrida. Endpoint según https://flightpowers.com/docs
# (Google Hotels live). Guarda flightpowers_hoteles.csv con columnas
# periodo, ciudad, hotel, precio, moneda, fecha_consulta.
HOTELS_PATH = "/v1/hotels/search"
HOTEL_CITY = "Medellin"
MAX_HOTEL_CALLS = 2
HOTEL_COLUMNS = ["periodo", "ciudad", "hotel", "precio", "moneda", "fecha_consulta"]
OUT_HOTELES = "flightpowers_hoteles"


def _headers(key: str) -> dict:
    return {
        "x-api-key": key,
        "x-rapidapi-key": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _as_list(payload: object) -> list:
    """El API puede envolver en data/offers/results/flights/itineraries."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "offers", "results", "flights", "itineraries", "prices"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                for sub in ("data", "offers", "results", "flights", "itineraries"):
                    inner = val.get(sub)
                    if isinstance(inner, list):
                        return inner
    return []


def _precio_moneda(it: dict) -> tuple[float | None, str]:
    price = it.get("price")
    if isinstance(price, dict):
        raw = price.get("total", price.get("amount", price.get("value")))
        mon = str(price.get("currency", it.get("currency", "USD")))
    else:
        raw = price if price is not None else it.get("total", it.get("amount", it.get("fare")))
        mon = str(it.get("currency", "USD"))
    try:
        if raw is None:
            return None, mon or "USD"
        return float(raw), mon or "USD"
    except (TypeError, ValueError):
        return None, mon or "USD"


def parse_offers(payload: dict | list, origen: str, destino: str, hoy: str | None = None) -> pd.DataFrame:
    recs: list[dict] = []
    hoy = hoy or date.today().isoformat()
    for it in _as_list(payload):
        if not isinstance(it, dict):
            continue
        precio, moneda = _precio_moneda(it)
        if precio is None:
            continue
        dep = str(
            it.get("departure_date")
            or it.get("departureDate")
            or it.get("date")
            or it.get("outbound_date")
            or hoy
        )
        recs.append(
            {
                "periodo": dep[:7],
                "origen": str(it.get("origin", origen)),
                "destino": str(it.get("destination", destino)),
                "precio": precio,
                "moneda": moneda,
                "fecha_consulta": hoy,
            }
        )
    df = pd.DataFrame(recs).reindex(columns=COLUMNS)
    return df.dropna(subset=["precio"])


def _post_oneway(key: str, origen: str, destino: str, departure_date: str) -> dict | list | None:
    """POST defensivo: 401/429/cualquier error -> None (el caller hace SKIP/carry)."""
    try:
        r = requests.post(
            API_BASE + ONEWAY_PATH,
            headers=_headers(key),
            json={
                "origin": origen,
                "destination": destino,
                "departure_date": departure_date,
                "adults": 1,
                "currency": "USD",
            },
            timeout=40,
        )
        if r.status_code in (401, 403, 429):
            print(f"[flightpowers][WARN] HTTP {r.status_code} en {ONEWAY_PATH}")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[flightpowers][WARN] {ONEWAY_PATH} {origen}-{destino}: {e}")
        return None


def _hotel_precio_moneda(it: dict) -> tuple[float | None, str]:
    price = it.get("price")
    if isinstance(price, dict):
        raw = price.get("total", price.get("amount", price.get("value", price.get("nightly"))))
        mon = str(price.get("currency", it.get("currency", "USD")))
    else:
        raw = price if price is not None else it.get("total", it.get("amount", it.get("nightly_price")))
        mon = str(it.get("currency", "USD"))
    try:
        if raw is None:
            return None, mon or "USD"
        return float(raw), mon or "USD"
    except (TypeError, ValueError):
        return None, mon or "USD"


def parse_hotels(payload: dict | list, ciudad: str = HOTEL_CITY, hoy: str | None = None) -> pd.DataFrame:
    recs: list[dict] = []
    hoy = hoy or date.today().isoformat()
    for it in _as_list(payload):
        if not isinstance(it, dict):
            continue
        precio, moneda = _hotel_precio_moneda(it)
        if precio is None:
            continue
        nombre = str(
            it.get("hotel")
            or it.get("hotel_name")
            or it.get("name")
            or it.get("property_name")
            or ""
        )
        ciu = str(it.get("city") or it.get("ciudad") or ciudad)
        fecha = str(
            it.get("checkin")
            or it.get("check_in")
            or it.get("checkin_date")
            or it.get("date")
            or hoy
        )
        recs.append(
            {
                "periodo": fecha[:7],
                "ciudad": ciu,
                "hotel": nombre,
                "precio": precio,
                "moneda": moneda,
                "fecha_consulta": hoy,
            }
        )
    df = pd.DataFrame(recs).reindex(columns=HOTEL_COLUMNS)
    return df.dropna(subset=["precio"])


def _post_hotels(key: str, ciudad: str, checkin: str, checkout: str) -> dict | list | None:
    """POST defensivo hoteles: 401/429/cualquier error -> None (SKIP/carry)."""
    try:
        r = requests.post(
            API_BASE + HOTELS_PATH,
            headers=_headers(key),
            json={
                "city": ciudad,
                "checkin": checkin,
                "checkout": checkout,
                "adults": 2,
                "currency": "USD",
            },
            timeout=40,
        )
        if r.status_code in (401, 403, 429):
            print(f"[flightpowers][WARN] HTTP {r.status_code} en {HOTELS_PATH}")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[flightpowers][WARN] {HOTELS_PATH} {ciudad}: {e}")
        return None


def run_hotels() -> bool:
    key = os.environ.get("FLIGHTPOWERS_KEY", "")
    if not key:
        print(
            "[flightpowers][SKIP] hoteles sin FLIGHTPOWERS_KEY -> "
            "alta gratis en RapidAPI 'Google Flights Live API' "
            "(plan BASIC 10 req/mes sin tarjeta) y exportar la key en "
            "~/.bureau_backend_env. Docs: https://flightpowers.com/docs"
        )
        return False
    try:
        hoy = date.today()
        checkin = (hoy + timedelta(days=30)).isoformat()
        checkout = (hoy + timedelta(days=31)).isoformat()
        frames: list[pd.DataFrame] = []
        for _ in range(MAX_HOTEL_CALLS):
            payload = _post_hotels(key, HOTEL_CITY, checkin, checkout)
            if payload is not None:
                df = parse_hotels(payload, HOTEL_CITY)
                if not df.empty:
                    frames.append(df)
            if frames:
                break  # 1 respuesta con datos basta; no quemar cuota
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        save_or_carry(df, OUT_HOTELES, HOTEL_COLUMNS)
        if df.empty:
            print("[flightpowers][SKIP] hoteles sin datos nuevos -> verificar key/cuota RapidAPI")
            return False
        print(f"[flightpowers] hoteles OK ({len(df)} hoteles)")
        return True
    except Exception as e:
        print(f"[flightpowers][SKIP] hoteles {e}")
        try:
            save_or_carry(pd.DataFrame(), OUT_HOTELES, HOTEL_COLUMNS)
        except Exception as e:
            print(f"[flightpowers][WARN] carry hoteles fallido: {e}")
        return False


def run() -> bool:
    key = os.environ.get("FLIGHTPOWERS_KEY", "")
    if not key:
        print(
            "[flightpowers][SKIP] sin FLIGHTPOWERS_KEY -> "
            "alta gratis en RapidAPI 'Google Flights Live API' "
            "(plan BASIC 10 req/mes sin tarjeta) y exportar la key en "
            "~/.bureau_backend_env. Docs: https://flightpowers.com/docs"
        )
        return False
    try:
        hoy = date.today()
        departure_date = (hoy + timedelta(days=30)).isoformat()
        frames: list[pd.DataFrame] = []
        for org, dst in ROUTES[:MAX_CALLS]:
            payload = _post_oneway(key, org, dst, departure_date)
            if payload is not None:
                df = parse_offers(payload, org, dst)
                if not df.empty:
                    frames.append(df)
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        save_or_carry(df, OUT_NAME, COLUMNS)
        if df.empty:
            print("[flightpowers][SKIP] sin ofertas nuevas -> verificar key/cuota RapidAPI")
            return False
        print(f"[flightpowers] OK ({len(df)} ofertas)")
        return True
    except Exception as e:
        print(f"[flightpowers][SKIP] {e}")
        try:
            save_or_carry(pd.DataFrame(), OUT_NAME, COLUMNS)
        except Exception as e:
            print(f"[flightpowers][WARN] carry fallido: {e}")
        return False


if __name__ == "__main__":
    run()
