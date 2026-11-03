"""Avisos de viaje hacia Colombia de los mercados emisores.

Fuentes abiertas, sin key, verificadas 2026-11-02:
- EE. UU.: https://cadataapi.state.gov/api/TravelAdvisories
- Canadá: https://data.international.gc.ca/travel-voyage/cta-cap-co.json
- Reino Unido: https://www.gov.uk/api/content/foreign-travel-advice/colombia
"""

import re

import pandas as pd
import requests

from .base import UA, save_or_carry

COLUMNS = ["pais", "fuente", "nivel", "titulo", "actualizado", "resumen", "url"]
_TAGS = re.compile(r"<[^>]+>")


def _txt(value, n=280) -> str:
    text = _TAGS.sub(" ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:n]


def fila_us(item: dict) -> dict | None:
    cats = item.get("Category") or []
    if "CO" not in cats:
        return None
    return {
        "pais": "Estados Unidos",
        "fuente": "US State Dept",
        "nivel": _txt(item.get("Title"), 80),
        "titulo": _txt(item.get("Title"), 120),
        "actualizado": str(item.get("Updated") or "")[:25],
        "resumen": _txt(item.get("Summary")),
        "url": item.get("Link") or "",
    }


def fila_ca(payload: dict) -> dict | None:
    data = (payload or {}).get("data") or {}
    eng = data.get("eng") or {}
    if not eng:
        return None
    return {
        "pais": "Canadá",
        "fuente": "Global Affairs Canada",
        "nivel": _txt(eng.get("advisory-text"), 120),
        "titulo": "Colombia",
        "actualizado": _txt(eng.get("friendly-date"), 40),
        "resumen": _txt(eng.get("recent-updates")),
        "url": "https://travel.gc.ca/destinations/colombia",
    }


def fila_uk(payload: dict) -> dict | None:
    if not payload:
        return None
    details = payload.get("details") or {}
    niveles = details.get("alert_status") or []
    nivel = ", ".join(str(x) for x in niveles) if isinstance(niveles, list) else str(niveles)
    return {
        "pais": "Reino Unido",
        "fuente": "FCDO",
        "nivel": _txt(nivel, 120),
        "titulo": _txt(payload.get("title"), 120),
        "actualizado": str(payload.get("public_updated_at") or "")[:25],
        "resumen": _txt(details.get("change_description")),
        "url": "https://www.gov.uk/foreign-travel-advice/colombia",
    }


def _vacio() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def run():
    filas = []
    try:
        r = requests.get("https://cadataapi.state.gov/api/TravelAdvisories", headers=UA, timeout=60)
        r.raise_for_status()
        for item in r.json() or []:
            fila = fila_us(item)
            if fila:
                filas.append(fila)
                break
    except Exception as e:
        print(f"[extract][WARN] avisos US: {e}")
    try:
        r = requests.get("https://data.international.gc.ca/travel-voyage/cta-cap-co.json", headers=UA, timeout=60)
        r.raise_for_status()
        fila = fila_ca(r.json())
        if fila:
            filas.append(fila)
    except Exception as e:
        print(f"[extract][WARN] avisos CA: {e}")
    try:
        r = requests.get("https://www.gov.uk/api/content/foreign-travel-advice/colombia", headers=UA, timeout=60)
        r.raise_for_status()
        fila = fila_uk(r.json())
        if fila:
            filas.append(fila)
    except Exception as e:
        print(f"[extract][WARN] avisos UK: {e}")
    df = pd.DataFrame(filas).reindex(columns=COLUMNS) if filas else _vacio()
    try:
        return [save_or_carry(df, "avisos_viaje", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] avisos_viaje save: {e}")
        return []


if __name__ == "__main__":
    run()
