"""Capacidad aérea EE. UU.–Colombia (BTS T-100, data.bts.gov 56rv-9p75).

El resumen por aeropuerto de origen no trae MDE. El resumen por país sí
trae asientos y pasajeros de las aerolíneas que reportan a EE. UU.
con Colombia. inbound_international_1 es el campo de pasajeros; el de
asientos viene nombrado inbound_international_seats.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COLUMNS = [
    "year", "mes", "llegadas_vuelos", "llegadas_pax", "llegadas_sillas",
    "salidas_vuelos", "salidas_pax", "salidas_sillas",
]
URL = "https://data.bts.gov/resource/56rv-9p75.json"


def filas(payload) -> pd.DataFrame:
    recs = []
    for row in payload or []:
        if str(row.get("country") or "") != "CO":
            continue
        fecha = str(row.get("date") or "")
        recs.append({
            "year": fecha[:4] or row.get("year"),
            "mes": fecha[5:7],
            "llegadas_vuelos": row.get("inbound_international"),
            "llegadas_pax": row.get("inbound_international_1"),
            "llegadas_sillas": row.get("inbound_international_seats"),
            "salidas_vuelos": row.get("outbound_international"),
            "salidas_pax": row.get("outbound_international_1"),
            "salidas_sillas": row.get("outbound_international_seats"),
        })
    df = pd.DataFrame(recs).reindex(columns=COLUMNS)
    if not df.empty:
        df = df.sort_values(["year", "mes"])
    return df


def _vacio() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run():
    df = _vacio()
    try:
        r = requests.get(
            URL,
            params={"country": "CO", "$order": "date DESC", "$limit": "24"},
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        df = filas(r.json())
        print(f"[extract] bts_co: {len(df)} meses")
    except Exception as e:
        print(f"[extract][WARN] bts_co: {e}")
    try:
        return [save_or_carry(df, "bts_co", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] bts_co save: {e}")
        return []


if __name__ == "__main__":
    run()
