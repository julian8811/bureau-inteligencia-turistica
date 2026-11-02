"""GDELT marca: escucha gratuita de noticias globales sobre Medellín turismo (reemplazo gratis de Brand24).
Estrategia 01-nov fast-fail (fuentes-warn-dead-skip S3: GDELT muerta, 429 siempre, 0 filas):
- 1 sola query combinada/día (menos requests = menos ban)
- 429 -> SKIP directo sin reintento (el carry-forward cubre; reintentar quema ~7 min del daily)
- error de red (conexion/timeout) -> 1 unico reintento corto de 5s
- resto de errores -> SKIP directo; jamas levanta, mismo CSV via save_or_carry
"""
import time
import requests
import pandas as pd
from .base import save_or_carry

QUERY = '("Medellin" AND (tourism OR turismo OR travel OR hotel OR "Bureau"))'
COLS = ["date", "value", "query"]
NETWORK_RETRY_WAIT = 5
_NETWORK_ERRORS = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)

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

def _is_rate_limited(exc: Exception) -> bool:
    resp = getattr(exc, "response", None)
    if resp is not None and getattr(resp, "status_code", None) == 429:
        return True
    return "429" in str(exc)


def run():
    # Fast-fail: GDELT responde 429 siempre (ambos lados caidos). 1 intento;
    # ante 429 SKIP directo, ante error de red 1 reintento de 5s, resto SKIP.
    df = pd.DataFrame()
    try:
        df = timeseries_once(QUERY)
    except Exception as e:
        if _is_rate_limited(e):
            print(f"[gdelt][SKIP] 429 rate-limit, sin reintento -> carry; {str(e)[:120]}")
        elif isinstance(e, _NETWORK_ERRORS):
            print(f"[gdelt][WARN] error de red, 1 reintento en {NETWORK_RETRY_WAIT}s: {str(e)[:120]}")
            time.sleep(NETWORK_RETRY_WAIT)
            try:
                df = timeseries_once(QUERY)
            except Exception as e2:
                print(f"[gdelt][SKIP] reintento fallido -> carry; {str(e2)[:120]}")
        else:
            print(f"[gdelt][SKIP] {str(e)[:150]} -> carry")
    return save_or_carry(df, "gdelt_marca", columns=COLS)

if __name__ == "__main__":
    run()
