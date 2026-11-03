"""TRM oficial (Superfinanciera, datos.gov.co 32sa-8pi3).

La serie vigente reemplaza el proxy de open.er-api. Si Socrata falla,
se usa ese proxy como respaldo de un solo día. Columnas estables:
base, date, rate_cop. Carry-forward si ambas fuentes fallan.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

COLUMNS = ["base", "date", "rate_cop"]
OFICIAL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
RESPALDO = "https://open.er-api.com/v6/latest/USD"


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def rows_from_socrata(payload) -> pd.DataFrame:
    recs = []
    for row in payload or []:
        valor = row.get("valor")
        desde = str(row.get("vigenciadesde") or "")[:10]
        if not desde or valor in (None, ""):
            continue
        recs.append({"base": "USD", "date": desde, "rate_cop": valor})
    df = pd.DataFrame(recs).reindex(columns=COLUMNS)
    if not df.empty:
        df = df.drop_duplicates("date").sort_values("date")
    return df


def run_rate() -> pd.DataFrame:
    try:
        r = requests.get(
            OFICIAL,
            params={"$order": "vigenciadesde DESC", "$limit": "40"},
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        df = rows_from_socrata(r.json())
        if not df.empty:
            print(f"[extract] trm_co oficial: {len(df)} filas (COP={df['rate_cop'].iloc[-1]})")
            return df
    except Exception as e:
        print(f"[extract][WARN] trm_co oficial: {e}")
    try:
        r = requests.get(RESPALDO, headers=UA, timeout=60)
        r.raise_for_status()
        payload = r.json()
        cop = ((payload or {}).get("rates") or {}).get("COP")
        fecha = str(payload.get("time_last_update_utc") or "")[:16]
        df = pd.DataFrame([{"base": "USD", "date": fecha, "rate_cop": cop}]).reindex(columns=COLUMNS)
        print(f"[extract] trm_co respaldo: COP={cop}")
        return df
    except Exception as e:
        print(f"[extract][WARN] trm_co respaldo: {e}")
        return _empty()


def run():
    try:
        df = run_rate()
    except Exception as e:
        print(f"[extract][WARN] trm_co agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "trm_co", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] trm_co save: {e}")
        return []


if __name__ == "__main__":
    run()
