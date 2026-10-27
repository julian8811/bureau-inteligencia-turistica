"""GDELT marca: escucha gratuita de noticias globales sobre Medellín turismo (reemplazo gratis de Brand24).
Respeta 1 req / 5s. Si responde 429, guarda stub y sigue (igual que google_trends).
Modo timeseries = volumen por día, ideal para picos (Ritvales, Feria Flores, premios).
"""
import time
import requests
import pandas as pd
from .base import save

QUERIES = {
    "medellin_turismo": "Medellin tourism",
    "medellin_bureau": '"Bureau Medellin" OR "Greater Medellin"',
    "medellin_seguridad": "Medellin seguridad turista",
}

def timeseries(query: str) -> pd.DataFrame:
    try:
        time.sleep(6)  # límite GDELT
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": query, "mode": "timelinevol", "format": "json", "timespan": "7days"},
            timeout=30,
        )
        if r.status_code == 429:
            print(f"[gdelt][WARN] 429 para {query}, reintento omitido hoy")
            return pd.DataFrame()
        r.raise_for_status()
        data = r.json().get("timeline", [{}])[0].get("data", [])
        df = pd.DataFrame(data)
        df["query"] = query
        return df
    except Exception as e:
        print(f"[gdelt][WARN] {query}: {e}")
        return pd.DataFrame()

def run():
    frames = [timeseries(q) for q in QUERIES.values()]
    df = pd.concat(frames, ignore_index=True) if any(not f.empty for f in frames) else pd.DataFrame()
    return save(df, "gdelt_marca")

if __name__ == "__main__":
    run()
