"""Emisores contexto via Graph Countries raw — contexto pais para top emisores.

Pivot canienter: Can I enter cobra API a empresas ("API de pago por solicitud")
-> NO se cablea por regla solo-gratis. En su lugar moneda, idiomas, region
y fronteras por cca3 desde Graph Countries raw (github, sin key).

Fuentes free sin key (intento en orden):
  primary:  https://raw.githubusercontent.com/lennertVanSever/graphcountries/main/data/countries.json
  fallback: https://raw.githubusercontent.com/mledoze/countries/world.lite/data/countries.json
Si ambas fallan -> vacio + carry-forward, nunca tumba el daily.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

PRIMARY_URL = "https://raw.githubusercontent.com/lennertVanSever/graphcountries/main/data/countries.json"
FALLBACK_URL = "https://raw.githubusercontent.com/mledoze/countries/world.lite/data/countries.json"

TOP_EMISORES = ["USA", "MEX", "ESP", "PAN", "ECU", "PER", "BRA", "COL"]
COLUMNS = ["cca3", "nombre", "region", "moneda", "idiomas", "fronteras"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _nombre(row: dict) -> str:
    name = row.get("name", "")
    if isinstance(name, dict):
        return str(name.get("common", "") or "")
    return str(name or "")


def _moneda(row: dict) -> str:
    cur = row.get("currencies", row.get("currency", ""))
    if isinstance(cur, dict):
        return ",".join(sorted(str(k) for k in cur if k))
    if isinstance(cur, list):
        return ",".join(sorted(str(c) for c in cur if c))
    return str(cur or "")


def _idiomas(row: dict) -> str:
    lang = row.get("languages", row.get("langs", ""))
    if isinstance(lang, dict):
        return ",".join(sorted(str(v) for v in lang.values() if v))
    if isinstance(lang, list):
        return ",".join(sorted(str(v) for v in lang if v))
    return str(lang or "")


def _fronteras(row: dict) -> str:
    b = row.get("borders", row.get("border", []) or [])
    if isinstance(b, list):
        return ",".join(sorted(str(x) for x in b if x))
    return str(b or "")


def parse_countries(payload) -> pd.DataFrame:
    """Parsea el raw de countries a COLUMNS; filtra top emisores si >500 filas."""
    try:
        if isinstance(payload, dict):
            if isinstance(payload.get("countries"), list):
                items = payload["countries"]
            else:
                items = []
                for k, v in payload.items():
                    if isinstance(v, dict):
                        v = dict(v)
                        v.setdefault("cca3", k)
                        items.append(v)
        elif isinstance(payload, list):
            items = payload
        else:
            return _empty()
        recs = []
        for row in items:
            if not isinstance(row, dict):
                continue
            cca3 = str(row.get("cca3", "") or "").upper()
            if not cca3:
                continue
            recs.append(
                {
                    "cca3": cca3,
                    "nombre": _nombre(row),
                    "region": str(row.get("region", "") or ""),
                    "moneda": _moneda(row),
                    "idiomas": _idiomas(row),
                    "fronteras": _fronteras(row),
                }
            )
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        if len(df) > 500:
            df = pd.DataFrame(df[df["cca3"].isin(TOP_EMISORES)]).reset_index(drop=True)
        print(f"[extract] emisores_contexto parse: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] emisores_contexto parse: {e}")
        return _empty()


def _fetch(url: str):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def run():
    """run() agregador: primary + fallback, guarda data/raw/<hoy>/emisores_contexto.csv."""
    try:
        try:
            df = parse_countries(_fetch(PRIMARY_URL))
        except Exception as e:
            print(f"[extract][WARN] emisores_contexto primary: {e}")
            df = _empty()
        if df.empty:
            try:
                df = parse_countries(_fetch(FALLBACK_URL))
            except Exception as e:
                print(f"[extract][WARN] emisores_contexto fallback: {e}")
                df = _empty()
        print(f"[extract] emisores_contexto: {len(df)} filas")
    except Exception as e:
        print(f"[extract][WARN] emisores_contexto agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "emisores_contexto", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] emisores_contexto save: {e}")
        return []


if __name__ == "__main__":
    run()
