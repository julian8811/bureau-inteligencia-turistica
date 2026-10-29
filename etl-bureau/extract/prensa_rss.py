"""Prensa RSS: El Colombiano + Alcaldía + MinCIT (marca noticias).
feedparser sobre RSS públicos, sin key ni login.
Trazabilidad S4: marca (cobertura y narrativa del destino).
"""

import feedparser
import pandas as pd

from .base import save_or_carry

FEEDS = [
    {
        "medio": "el_colombiano_medellin",
        "url": "https://www.elcolombiano.com/rss/medellin",
    },
    {
        "medio": "el_colombiano_economia",
        "url": "https://www.elcolombiano.com/rss/economia",
    },
    {"medio": "alcaldia_medellin", "url": "https://www.medellin.gov.co/es/feed/"},
    {"medio": "mincit_prensa", "url": "https://www.mincit.gov.co/prensa/rss"},
]
COLS = ["medio", "titulo", "link", "fecha"]
LIMIT = 200


def run_medio(feed: dict) -> pd.DataFrame:
    """Individual por medio: devuelve df (vacío si falla, nunca levanta)."""
    try:
        f = feedparser.parse(feed["url"], agent="bureau-etl/1.0")
        rows = []
        for e in f.entries:
            rows.append(
                {
                    "medio": feed["medio"],
                    "titulo": e.get("title", ""),
                    "link": e.get("link", ""),
                    "fecha": e.get("published", ""),
                }
            )
        return pd.DataFrame(rows, columns=COLS)
    except Exception as e:
        print(f"[extract][WARN] prensa_rss {feed.get('medio')}: {str(e)[:150]}")
        return pd.DataFrame(columns=COLS)


def run(feeds: list[dict] | None = None):
    """Agregador: 4 medios -> data/raw/<hoy>/prensa_rss.csv (carry si hoy falla)."""
    try:
        feeds = feeds if feeds is not None else FEEDS
        frames = [run_medio(f) for f in feeds]
        df = (
            pd.concat(frames, ignore_index=True)
            if frames
            else pd.DataFrame(columns=COLS)
        )
        df = df.head(LIMIT)
        print(f"[extract] prensa_rss: {len(df)} notas en {len(feeds)} medios")
        return save_or_carry(df, "prensa_rss", columns=COLS)
    except Exception as e:
        print(f"[extract][WARN] prensa_rss agregador: {str(e)[:150]}")
        return save_or_carry(pd.DataFrame(columns=COLS), "prensa_rss", columns=COLS)


if __name__ == "__main__":
    run()
