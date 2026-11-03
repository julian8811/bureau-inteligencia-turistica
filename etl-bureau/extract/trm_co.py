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


def mensual_desde_diaria(df: pd.DataFrame) -> pd.DataFrame:
    """Promedio del mes calendario. periodo YYYY-MM y trm a 2 decimales."""
    vacio = pd.DataFrame(columns=["periodo", "trm"])
    if df is None or df.empty or "date" not in df.columns or "rate_cop" not in df.columns:
        return vacio
    work = df.copy()
    work["periodo"] = work["date"].astype(str).str.slice(0, 7)
    work["rate_cop"] = pd.to_numeric(work["rate_cop"], errors="coerce")
    work = work.dropna(subset=["periodo", "rate_cop"])
    work = work[work["periodo"].str.match(r"\d{4}-\d{2}")]
    if work.empty:
        return vacio
    grupo = work.groupby("periodo", as_index=False)["rate_cop"].mean()
    grupo["trm"] = grupo["rate_cop"].map(float)
    return grupo[["periodo", "trm"]].sort_values("periodo").reset_index(drop=True)


def fetch_historia() -> pd.DataFrame:
    """TRM diaria desde 2015, para el promedio mensual. Vacío si Socrata no responde."""
    try:
        r = requests.get(
            OFICIAL,
            params={
                "$select": "vigenciadesde,valor",
                "$where": "vigenciadesde >= '2015-01-01T00:00:00.000'",
                "$order": "vigenciadesde",
                "$limit": "20000",
            },
            headers=UA,
            timeout=90,
        )
        r.raise_for_status()
        return rows_from_socrata(r.json())
    except Exception as e:
        print(f"[extract][WARN] trm_co historia: {e}")
        return _empty()


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
        rutas = [save_or_carry(df, "trm_co", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] trm_co save: {e}")
        rutas = []
    try:
        mensual = mensual_desde_diaria(fetch_historia())
        if not mensual.empty:
            save_or_carry(mensual, "trm_mensual", ["periodo", "trm"])
    except Exception as e:
        print(f"[extract][WARN] trm_mensual: {e}")
    return rutas


if __name__ == "__main__":
    run()
