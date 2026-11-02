"""OpenSky Network: tráfico aéreo en vivo sobre Medellín (MDE/SKRG + EOH/SKMD).

GET https://opensky-network.org/api/states/all (bbox Valle de Aburrá/Oriente).
API pública sin key, con rate-limit estricto: 429 o error de red ->
SKIP honesto con carry-forward, nunca inventar posiciones.
NOTA (30-oct-2026): /api/flights/(arrival|departure) devuelve 403 para
usuarios anónimos -> solo snapshot states, sin flujos.
Barrido 01-nov (S2): se mantiene states-only deliberadamente; /flights queda
FUERA (403 anonimo). Ante 429 en states, un unico reintento con ventana
menor (BBOX_SMALL); si sigue 429 -> SKIP con carry, nunca levanta.
"""
from datetime import date

import pandas as pd
import requests

from .base import UA, save_or_carry

STATES = "https://opensky-network.org/api/states/all"
BBOX = {"lamin": 5.8, "lamax": 6.7, "lomin": -76.1, "lomax": -75.1}
# Ventana menor para el reintento tras 429 (mitad de lat/lon aprox).
BBOX_SMALL = {"lamin": 6.0, "lamax": 6.5, "lomin": -75.7, "lomax": -75.4}

COLUMNS_STATES = ["periodo", "icao24", "vuelo", "pais", "lat", "lon",
                  "altitud_m", "en_tierra", "fecha_consulta"]
def parse_states(payload: dict) -> pd.DataFrame:
    recs: list[dict] = []
    hoy = date.today().isoformat()
    for s in (payload or {}).get("states") or []:
        try:
            recs.append({"periodo": hoy, "icao24": s[0],
                         "vuelo": (s[1] or "").strip(), "pais": s[2],
                         "lat": s[6], "lon": s[5], "altitud_m": s[7],
                         "en_tierra": bool(s[8]), "fecha_consulta": hoy})
        except (IndexError, TypeError):
            continue
    return pd.DataFrame(recs).reindex(columns=COLUMNS_STATES)


def _get(url: str, params: dict) -> requests.Response | None:
    try:
        r = requests.get(url, params=params, headers=UA, timeout=40)
        if r.status_code == 429:
            print(f"[opensky][WARN] 429 rate-limit en {url}")
            return None
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"[opensky][WARN] {url}: {e}")
        return None


def run() -> bool:
    # states-only: /flights queda fuera (403 para anonimos). Un unico
    # reintento con ventana menor si hay 429; si no, SKIP con carry.
    try:
        r = _get(STATES, BBOX)
        if r is None:
            print("[opensky][WARN] reintento con ventana menor tras 429")
            r = _get(STATES, BBOX_SMALL)
        if r is None:
            print("[opensky][SKIP] states no disponible")
            return False
        df = parse_states(r.json())
        save_or_carry(df, "opensky_states", COLUMNS_STATES)
        print(f"[opensky] OK ({len(df)} en vuelo sobre MDE/EOH)")
        return True
    except Exception as e:
        print(f"[opensky][SKIP] {e}")
        return False


if __name__ == "__main__":
    run()
