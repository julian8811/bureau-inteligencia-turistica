"""Wikimedia pageviews: interés destino Medellín (marca).
Artículos ES: Medellín, Feria_de_las_Flores, Metro_de_Medellín.
API pública sin key: wikimedia.org pageviews per-article/daily.
Trazabilidad S4: marca (interés destino, proxy de búsquedas/demanda).
"""

from datetime import date, timedelta

import pandas as pd
import requests

from .base import UA, save_or_carry

ARTICLES = {
    "medellin": "Medellín",
    "feria_flores": "Feria_de_las_Flores",
    "metro_medellin": "Metro_de_Medellín",
}
COLS = ["articulo", "timestamp", "views"]
WINDOW_DAYS = 30
LIMIT = 200


def _window():
    end = date.today()
    start = end - timedelta(days=WINDOW_DAYS)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def run_articulo(clave: str) -> pd.DataFrame:
    """Individual por artículo: devuelve df (vacío si falla, nunca levanta)."""
    try:
        art = ARTICLES[clave]
        ini, fin = _window()
        url = (
            "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"es.wikipedia/all-access/all-agents/{art}/daily/{ini}/{fin}"
        )
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        items = r.json().get("items", [])
        rows = [
            {
                "articulo": clave,
                "timestamp": it.get("timestamp", ""),
                "views": it.get("views", 0),
            }
            for it in items
        ]
        return pd.DataFrame(rows, columns=COLS)
    except Exception as e:
        print(f"[extract][WARN] wikimedia_views {clave}: {str(e)[:150]}")
        return pd.DataFrame(columns=COLS)


def run():
    """Agregador: 3 artículos -> data/raw/<hoy>/wikimedia_views.csv (carry si hoy falla)."""
    try:
        frames = [run_articulo(k) for k in ARTICLES]
        df = (
            pd.concat(frames, ignore_index=True)
            if frames
            else pd.DataFrame(columns=COLS)
        )
        df = df.head(LIMIT)
        print(
            f"[extract] wikimedia_views: {len(df)} filas en {len(ARTICLES)} artículos"
        )
        return save_or_carry(df, "wikimedia_views", columns=COLS)
    except Exception as e:
        print(f"[extract][WARN] wikimedia_views agregador: {str(e)[:150]}")
        return save_or_carry(
            pd.DataFrame(columns=COLS), "wikimedia_views", columns=COLS
        )


if __name__ == "__main__":
    run()
