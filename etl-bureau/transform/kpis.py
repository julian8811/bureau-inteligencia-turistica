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
    try:
        return pd.read_csv(cands[-1])
    except Exception as e:
        print(f"[transform][WARN] {name}: no se pudo leer ({e}) -> vacío")
        return pd.DataFrame()

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

def kpis_demanda() -> dict:
    """Demanda desde Socrata cableado: Medellín no-residentes + aéreo MDE/EOH."""
    med = latest_raw("medellin_no_residentes")
    aer = latest_raw("aereo_mde_eoh")
    out: dict = {}
    try:
        if not med.empty and "cant_extranjeros_no_residentes" in med.columns:
            med["cant_extranjeros_no_residentes"] = pd.to_numeric(med["cant_extranjeros_no_residentes"], errors="coerce").fillna(0)
            out["llegadas_medellin_nr"] = int(med["cant_extranjeros_no_residentes"].sum())
            if "paisoeeresidencia" in med.columns:
                top = med.groupby("paisoeeresidencia")["cant_extranjeros_no_residentes"].sum().sort_values(ascending=False).head(5)
                out["top1_emisor"] = str(top.index[0]) if len(top) else ""
                out["share_top5"] = round(top.sum() / max(med["cant_extranjeros_no_residentes"].sum(), 1), 3)
        if not aer.empty and "pasajeros" in aer.columns:
            aer["pasajeros"] = pd.to_numeric(aer["pasajeros"], errors="coerce").fillna(0)
            lleg = aer[aer.get("sentido", "") == "llegada"]["pasajeros"].sum() if "sentido" in aer.columns else 0
            sal = aer[aer.get("sentido", "") == "salida"]["pasajeros"].sum() if "sentido" in aer.columns else 0
            out["pax_llegadas_mde"] = int(lleg)
            out["pax_salidas_mde"] = int(sal)
    except Exception as e:
        print(f"[transform][WARN] kpis_demanda: {e}")
    return out

def kpis_dane() -> dict:
    egit = latest_raw("dane_egit_gasto_dia")
    enh = latest_raw("dane_enh")
    out = {"dane_egit_ok": int(not egit.empty), "dane_enh_ok": int(not enh.empty),
           "dane_egit_filas": int(len(egit)), "dane_enh_filas": int(len(enh))}
    try:
        # Gasto promedio día último trimestre disponible (serie nacional 24 ciudades, proxy gasto)
        if not egit.empty and {"trimestre", "valor"} <= set(egit.columns):
            last = egit["trimestre"].dropna().unique().tolist()[-1]
            sub = egit[egit["trimestre"] == last]
            total = sub[sub["concepto"].astype(str).str.contains("Total|total", na=False)]["valor"]
            if not total.empty:
                out["gasto_prom_dia_cop"] = float(pd.to_numeric(total, errors="coerce").dropna().iloc[0])
                out["gasto_trimestre"] = str(last)
    except Exception as e:
        print(f"[transform][WARN] kpis_dane gasto: {e}")
    return out

def kpis_gdelt() -> dict:
    g = latest_raw("gdelt_marca")
    if g.empty:
        return {"gdelt_vol_7d": 0}
    vol = pd.to_numeric(g.get("value", 0), errors="coerce").fillna(0).sum() if "value" in g.columns else len(g)
    return {"gdelt_vol_7d": int(vol), "gdelt_queries": int(g["query"].nunique()) if "query" in g.columns else 0}

def run():
    PROC.mkdir(parents=True, exist_ok=True)
    hoy = date.today().isoformat()
    trends = latest_raw("google_trends")
    alerts = latest_raw("alerts_rss")
    marca = kpis_marca(alerts)
    dem = kpis_demanda()
    dan = kpis_dane()
    gde = kpis_gdelt()
    print(f"[transform] trends={len(trends)} alerts={len(alerts)} marca={marca} dem={dem} dane={dan} gdelt={gde}")

    # CRM interno (gated manual): si el Bureau deja su Excel en data/raw/manual/crm.xlsx se calculan KPIs MICE
    crm_path = RAW / "manual" / "crm.xlsx"
    mice = {}
    if crm_path.exists():
        crm = pd.read_excel(crm_path)
        # alias de columnas plantilla (gasto_prom_usd, estadia_noches, valor_rfp_usd)
        crm = crm.rename(columns={"gasto_prom_usd": "gasto_prom", "estadia_noches": "estadia", "valor_rfp_usd": "valor_rfp"})
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

    kpi = pd.DataFrame([{"fecha": hoy, **marca, **dem, **dan, **gde, **mice}])
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
