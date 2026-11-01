"""Conectividad aérea MDE/EOH (emisores vacacionales + llegadas MICE).
- OurAirports airports.csv (verificado 28-oct-2026): ficha de MDE/EOH + Antioquia.
- OpenFlights routes.dat (verificado 28-oct-2026): rutas con origen/destino MDE o EOH.
Sin key, timeout ≤25s, carry-forward si hoy falla. Nunca tumba el daily.
"""
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from .base import UA, save_or_carry

AIRPORTS = "https://ourairports.com/data/airports.csv"
ROUTES = "https://openflights.org/data/routes.dat"
ROUTE_COLS = ["aerolinea", "aerolinea_id", "origen", "origen_id", "destino",
              "destino_id", "codeshare", "escalas", "equipos"]
TARGETS = {"MDE", "EOH"}


def run_aeropuertos() -> Path:
    df = pd.DataFrame()
    try:
        r = requests.get(AIRPORTS, headers=UA, timeout=25)
        r.raise_for_status()
        full = pd.read_csv(StringIO(r.text))
        has_co = "iso_country" in full.columns
        recs = []
        for row in full.to_dict(orient="records"):
            if has_co and row.get("iso_country") != "CO":
                continue
            iata = str(row.get("iata_code", ""))
            ident = str(row.get("ident", ""))
            muni = str(row.get("municipality", "")).upper()
            if (iata in ("MDE", "EOH") or ident in ("SKRG", "SKMD")
                    or "MEDELL" in muni or "RIONEGRO" in muni):
                recs.append(row)
        df = pd.DataFrame.from_records(recs)
    except Exception as e:
        print(f"[conectividad_aerea][WARN] aeropuertos: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "conectividad_aeropuertos")


def run_rutas() -> Path:
    df = pd.DataFrame()
    try:
        r = requests.get(ROUTES, headers=UA, timeout=25)
        r.raise_for_status()
        full = pd.read_csv(StringIO(r.text), header=None, names=ROUTE_COLS)
        rows = [row for row in full.to_dict(orient="records")
                if row.get("origen") in ("MDE", "EOH")
                or row.get("destino") in ("MDE", "EOH")]
        df = pd.DataFrame.from_records(rows)
        df["via_mde_eoh"] = [
            "origen" if row.get("origen") in ("MDE", "EOH") else "destino"
            for row in rows
        ]
        df["via_mde_eoh"] = df.apply(
            lambda x: "origen" if x["origen"] in TARGETS else "destino", axis=1)
    except Exception as e:
        print(f"[conectividad_aerea][WARN] rutas: {str(e)[:150]}")
        df = pd.DataFrame()
    return save_or_carry(df, "conectividad_rutas_mde_eoh")


def run() -> list[Path]:
    return [run_aeropuertos(), run_rutas()]


if __name__ == "__main__":
    run()
