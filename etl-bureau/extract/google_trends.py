"""Google Trends: intención de búsqueda hacia Medellín por mercado emisor. Gratis, TOS ok vía pytrends."""
from pytrends.request import TrendReq
import pandas as pd
from .base import save

KEYWORDS = ["vuelos Medellín", "hoteles Medellín", "Medellín travel"]
GEOS = {"US": "Estados Unidos", "ES": "España", "MX": "México", "PA": "Panamá", "PE": "Perú"}

def run():
    try:
        pt = TrendReq(hl="es", tz=-300)
        frames = []
        for geo in GEOS:
            pt.build_payload(KEYWORDS, timeframe="today 3-m", geo=geo)
            df = pt.interest_over_time().reset_index()
            if df.empty:
                continue
            df["geo"] = geo
            frames.append(df)
        out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", *KEYWORDS, "geo"])
        return save(out, "google_trends")
    except Exception as e:
        print(f"[extract][WARN] google_trends falló: {e}")
        return save(pd.DataFrame(columns=["date", *KEYWORDS, "geo"]), "google_trends")

if __name__ == "__main__":
    run()
