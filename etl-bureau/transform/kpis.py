"""Transform: raw diario -> modelo estrella + KPIs del Plan Dashboard (pestaña Excel).
Tablas: fact_demanda, fact_mice, fact_marca, dim_fecha, dim_mercado.
Fórmulas espejo del Excel: win_rate=ganados/recibidos, derrama=asist*gasto*estadía,
revpar=occ*adr, sentimiento=(pos-neg)/total, engagement=inter/alcance.
"""
from pathlib import Path
from datetime import date
import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

def latest_raw(name: str) -> pd.DataFrame:
    cands = sorted(RAW.glob(f"*/{name}.csv"))
    if not cands:
        return pd.DataFrame()
    return pd.read_csv(cands[-1])

def kpis_marca(alerts: pd.DataFrame) -> dict:
    if alerts.empty:
        return {"menciones": 0, "sentimiento_neto": 0.0, "share_medellin": 0.0}
    t = alerts["titulo"].str.lower().fillna("")
    pos = t.str.contains("récord|premio|líder|crece|top|galardón|inaugura").sum()
    neg = t.str.contains("insegur|homicidio|estafa|cancel|crisis|colapso|denuncia").sum()
    total = max(len(alerts), 1)
    med = t.str.contains("medell").sum()
    return {
        "menciones": int(len(alerts)),
        "sentimiento_neto": round((pos - neg) / total, 3),  # =(Pos-Neg)/Total
        "share_medellin": round(med / total, 3),
    }

def run():
    PROC.mkdir(parents=True, exist_ok=True)
    hoy = date.today().isoformat()
    trends = latest_raw("google_trends")
    alerts = latest_raw("alerts_rss")
    marca = kpis_marca(alerts)
    print(f"[transform] trends={len(trends)} alerts={len(alerts)} marca={marca}")

    # CRM interno (gated manual): si el Bureau deja su Excel en data/raw/manual/crm.xlsx se calculan KPIs MICE
    crm_path = RAW / "manual" / "crm.xlsx"
    mice = {}
    if crm_path.exists():
        crm = pd.read_excel(crm_path)
        # espera columnas: estado (recibido/ganado), asistentes, gasto_prom, estadia, valor_rfp, prob
        rec = len(crm)
        gan = len(crm[crm.get("estado", "") == "ganado"]) if "estado" in crm.columns else 0
        mice = {
            "win_rate": round(gan / max(rec, 1), 3),
            "noches_mice": float((crm.get("asistentes", 0) * crm.get("estadia", 0)).sum()) if {"asistentes", "estadia"} <= set(crm.columns) else 0,
            "derrama_mice": float((crm.get("asistentes", 0) * crm.get("gasto_prom", 0) * crm.get("estadia", 0)).sum()) if {"asistentes", "gasto_prom", "estadia"} <= set(crm.columns) else 0,
            "pipeline_ponderado": float((crm.get("valor_rfp", 0) * crm.get("prob", 0)).sum()) if {"valor_rfp", "prob"} <= set(crm.columns) else 0,
        }
    else:
        print("[transform][SKIP] sin data/raw/manual/crm.xlsx -> KPIs MICE en 0 hasta carga manual")
        mice = {"win_rate": 0, "noches_mice": 0, "derrama_mice": 0, "pipeline_ponderado": 0}

    kpi = pd.DataFrame([{"fecha": hoy, **marca, **mice}])
    p = PROC / f"kpis_{hoy}.csv"
    kpi.to_csv(p, index=False)
    # acumulado para Power BI
    hist = PROC / "kpis_historico.csv"
    if hist.exists():
        h = pd.read_csv(hist)
        h = pd.concat([h, kpi], ignore_index=True).drop_duplicates(subset=["fecha"], keep="last")
    else:
        h = kpi
    h.to_csv(hist, index=False)
    print(f"[transform] KPIs -> {p} + historico ({len(h)} días)")
    return p

if __name__ == "__main__":
    run()
