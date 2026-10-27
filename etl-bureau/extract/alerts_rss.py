"""Alerts RSS: Google Alerts + Talkwalker vía feed RSS del correo/lector.
El Bureau crea las alertas una vez ('Medellín turismo', 'Bureau Medellín', 'Feria de Flores', etc.)
y este script lee los RSS públicos. Sin scraping a Brand24.
CABLEADO 27-oct: Google News RSS + Reddit RSS funcionan SIN login (reemplazo directo de Google Alerts).
Talkwalker Alerts (gratis, solo email, sin tarjeta): https://www.talkwalker.com/alerts -> crear las mismas 5
keywords y pegar aquí el RSS que te mandan por mail.
"""
import feedparser
import pandas as pd
from urllib.parse import quote_plus
from .base import save

KEYWORDS = [
    "Medellín turismo",
    "Bureau Medellín",
    "Feria de Flores",
    "Ritvales Medellín",
    "turismo de reuniones Medellín",
]

def google_news_rss(q: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=es-419&gl=CO&ceid=CO:es-419"

def reddit_rss(q: str) -> str:
    return f"https://www.reddit.com/r/Medellin/search.rss?q={quote_plus(q)}&sort=new&restrict_sr=on"

# CABLEADAS: funcionan sin login ni API key
ALERT_FEEDS: list[str] = (
    [google_news_rss(k) for k in KEYWORDS]
    + [reddit_rss("turismo"), reddit_rss("Feria de Flores")]
    # + pegar aquí los RSS de Talkwalker Alerts cuando los creen (1 min, gratis):
    # "https://...talkwalker.../medellin-turismo",
)

def run(feeds: list[str] | None = None):
    feeds = feeds if feeds is not None else ALERT_FEEDS
    rows = []
    for url in feeds:
        try:
            f = feedparser.parse(url, agent="bureau-etl/1.0")
            for e in f.entries:
                rows.append({"feed": url, "titulo": e.get("title", ""), "link": e.get("link", ""), "fecha": e.get("published", "")})
        except Exception as ex:
            print(f"[extract][WARN] feed {url}: {ex}")
    df = pd.DataFrame(rows, columns=["feed", "titulo", "link", "fecha"])
    print(f"[extract] alerts_rss: {len(df)} menciones en {len(feeds)} feeds")
    return save(df, "alerts_rss")

if __name__ == "__main__":
    run()
