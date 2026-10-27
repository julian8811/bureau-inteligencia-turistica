"""Alerts RSS: Google Alerts + Talkwalker vía feed RSS del correo/lector.
El Bureau crea las alertas una vez ('Medellín turismo', 'Bureau Medellín', 'Feria de Flores', etc.)
y este script lee los RSS públicos. Sin scraping a Brand24."""
import feedparser
import pandas as pd
from .base import save

# Pegar aquí los RSS de las alertas (Feedbucket / Kill-the-newsletter / lector RSS)
ALERT_FEEDS: list[str] = []

def run(feeds: list[str] | None = None):
    feeds = feeds if feeds is not None else ALERT_FEEDS
    rows = []
    for url in feeds:
        try:
            f = feedparser.parse(url)
            for e in f.entries:
                rows.append({"feed": url, "titulo": e.get("title", ""), "link": e.get("link", ""), "fecha": e.get("published", "")})
        except Exception as ex:
            print(f"[extract][WARN] feed {url}: {ex}")
    df = pd.DataFrame(rows, columns=["feed", "titulo", "link", "fecha"])
    # Sentimiento neto básico se calcula en transform con léxico, Brand24 solo para validación puntual
    return save(df, "alerts_rss")

if __name__ == "__main__":
    run()
