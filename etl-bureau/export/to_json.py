"""Exporta el warehouse a JSON compacto para el sitio estático (sin servidor, sin licencias)."""
from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
RAW = BASE / "data" / "raw"
OUT = BASE / "web" / "data"

def latest_raw(name: str) -> pd.DataFrame:
    cands = sorted(RAW.glob(f"*/{name}.csv"))
    if not cands:
        return pd.DataFrame()
    try:
        return pd.read_csv(cands[-1])
    except Exception:
        return pd.DataFrame()

def jwrite(df: pd.DataFrame, name: str, max_rows: int | None = None):
    OUT.mkdir(parents=True, exist_ok=True)
    if max_rows:
        df = df.head(max_rows)
    df = df.where(pd.notnull(df), None)
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(df.to_dict(orient="records"), ensure_ascii=False))
    print(f"[export] {name}: {len(df)} filas -> {p}")
    return p

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    hist = pd.read_csv(PROC / "kpis_historico.csv") if (PROC / "kpis_historico.csv").exists() else pd.DataFrame()
    if not hist.empty:
        jwrite(hist.tail(1), "kpis")
    pais = pd.read_csv(PROC / "pais_dashboard.csv") if (PROC / "pais_dashboard.csv").exists() else pd.DataFrame()
    if not pais.empty:
        jwrite(pais.head(60), "paises")
    des = pd.read_csv(PROC / "destinos_dashboard.csv") if (PROC / "destinos_dashboard.csv").exists() else pd.DataFrame()
    if not des.empty:
        jwrite(des, "destinos")
    tre = latest_raw("google_trends")
    if not tre.empty:
        t = tre.melt(id_vars=["date", "geo"], value_vars=[c for c in tre.columns if c not in ("date", "geo", "isPartial")],
                     var_name="busqueda", value_name="indice")
        jwrite(t, "trends")
    al = latest_raw("alerts_rss")
    if not al.empty:
        jwrite(al.head(30), "menciones")
    gas = latest_raw("dane_egit_gasto_dia")
    if not gas.empty:
        gas["concepto"] = gas["concepto"].astype(str).str.strip().str.strip("'\"")
        tot = gas[gas["concepto"] == "Total 24 ciudades y áreas metropolitanas"].filter(["trimestre", "valor"]).copy()
        tot["valor"] = pd.to_numeric(tot["valor"], errors="coerce")
        tot = tot.dropna()
        jwrite(tot, "gasto_dane")
    u3m = PROC / "ult3m_pais.csv"
    if u3m.exists():
        jwrite(pd.read_csv(u3m).head(40), "ult3m_pais")
    for d in sorted(PROC.glob("desglose_*.csv")):
        try:
            df = pd.read_csv(d)
            jwrite(df.head(60), d.stem)
        except Exception as e:
            print(f"[export][WARN] {d.name}: {e}")
    occ = latest_raw("medata_ocupacion_med")
    if not occ.empty:
        jwrite(occ, "ocupacion_hist")
    print("[export] OK")

if __name__ == "__main__":
    run()
