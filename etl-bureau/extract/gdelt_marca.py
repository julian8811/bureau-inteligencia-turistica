"""GDELT marca: escucha gratuita de noticias globales sobre Medellín turismo (reemplazo gratis de Brand24).
Estrategia 28-oct anti-429:
- 1 sola query combinada/día (menos requests = menos ban)
- backoff corto (la IP puede estar baneada por horas; no quemar el cron) + carry-forward del último bueno
- volumen diario (timelinevol) ideal para picos: Feria, Ritvales, premios
"""
import time
import requests
import pandas as pd
from .base import save_or_carry

QUERY = '("Medellin" AND (tourism OR turismo OR travel OR hotel OR "Bureau"))'
COLS = ["date", "value", "query"]

def timeseries_once(query: str) -> pd.DataFrame:
    r = requests.get(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={"query": query, "mode": "timelinevol", "format": "json", "timespan": "7days"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json().get("timeline", [{}])[0].get("data", [])
    df = pd.DataFrame(data)
    df["query"] = "medellin_turismo_combined"
    return df

def run():
    # GDELT banea IPs con tráfico seguido: 2 intentos máx, el resto lo cubre el carry-forward
    df = pd.DataFrame()
    for wait in (0, 120):
        if wait:
            print(f"[gdelt] backoff {wait}s...")
            time.sleep(wait)
        try:
            time.sleep(6)  # límite GDELT: 1 req / 5s
            df = timeseries_once(QUERY)
            if not df.empty:
                break
        except Exception as e:
            print(f"[gdelt][WARN] intento fallido: {str(e)[:150]}")
    return save_or_carry(df, "gdelt_marca", columns=COLS)

if __name__ == "__main__":
    run()
