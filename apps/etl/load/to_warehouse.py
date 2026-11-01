"""Load: Parquet + SQLite + web/data JSON listos para Power BI y sitio estatico.

Lee etl-bureau/data/processed/*.csv (modelo estrella + KPIs + desgloses),
escribe:
  - data/processed/*.parquet (espejo por CSV)
  - data/processed/bureau.sqlite (una tabla por CSV)
  - web/data/*.json (para index.html e informe.html)

Nunca tumba el daily: cada archivo se exporta en try/except.
"""
from pathlib import Path
import json
import sqlite3
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
RAW = BASE / "data" / "raw"
WEBDATA = BASE / "web" / "data"

TABLE_MAP = {
    "kpis_historico": "kpis_diario",
    "pais_dashboard": "pais",
    "destinos_dashboard": "destinos",
    "ult3m_pais": "ult3m_pais",
}

WEB_MAP = {
    "kpis": "kpis_historico.csv",
    "paises": "pais_dashboard.csv",
    "destinos": "destinos_dashboard.csv",
    "ult3m_pais": "ult3m_pais.csv",
}


def _latest_raw(name: str) -> pd.DataFrame:
    cands = sorted(RAW.glob(f"*/{name}.csv"))
    if not cands:
        return pd.DataFrame()
    try:
        return pd.read_csv(cands[-1])
    except Exception as e:
        print(f"[load][WARN] raw {name}: {e}")
        return pd.DataFrame()


def _table_name(csv_path: Path) -> str:
    stem = csv_path.stem
    if stem in TABLE_MAP:
        return TABLE_MAP[stem]
    return stem.replace("-", "_").replace(" ", "_").lower()


def export_csv_to_sqlite_parquet(csv_path: Path, con: sqlite3.Connection) -> str:
    """Exporta un CSV a sqlite + parquet. Retorna nombre de tabla."""
    table = _table_name(csv_path)
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[load][WARN] {csv_path.name}: no se pudo leer ({e}) -> skip")
        return ""
    if df.empty:
        print(f"[load][SKIP] {csv_path.name} vacio -> skip")
        return ""
    try:
        df.to_sql(table, con, if_exists="replace", index=False)
    except Exception as e:
        print(f"[load][WARN] sqlite {table}: {e}")
    try:
        df.to_parquet(PROC / f"{csv_path.stem}.parquet", index=False)
    except Exception as e:
        print(f"[load][WARN] parquet {csv_path.stem}: {e}")
    return table


def export_web_json() -> dict:
    """Genera web/data/*.json desde PROC + RAW. Retorna {nombre: filas}."""
    WEBDATA.mkdir(parents=True, exist_ok=True)
    out: dict = {}
    # 1) Espejos directos PROC -> web
    for web_name, csv_name in WEB_MAP.items():
        p = PROC / csv_name
        if not p.exists():
            print(f"[load][SKIP] web/{web_name}.json sin {csv_name}")
            continue
        try:
            df = pd.read_csv(p)
            (WEBDATA / f"{web_name}.json").write_text(
                df.to_json(orient="records", force_ascii=False), encoding="utf-8"
            )
            out[web_name] = len(df)
        except Exception as e:
            print(f"[load][WARN] web {web_name}: {e}")
    # 2) Desgloses PROC -> web (mismo nombre)
    for p in sorted(PROC.glob("desglose_*.csv")):
        if p.name.endswith("_.csv"):
            print(f"[load][SKIP] artefacto duplicado {p.name} (termina en _)")
            continue
        try:
            df = pd.read_csv(p)
            (WEBDATA / f"{p.stem}.json").write_text(
                df.to_json(orient="records", force_ascii=False), encoding="utf-8"
            )
            out[p.stem] = len(df)
        except Exception as e:
            print(f"[load][WARN] web {p.stem}: {e}")
    # 3) Derivados desde RAW ultimo dia (lo que espera index.html/informe.html)
    try:
        gasto = _latest_raw("dane_egit_gasto_dia")
        if not gasto.empty and {"trimestre", "valor"} <= set(gasto.columns):
            g = gasto[["trimestre", "valor"]].copy()
            (WEBDATA / "gasto_dane.json").write_text(
                g.to_json(orient="records", force_ascii=False), encoding="utf-8"
            )
            out["gasto_dane"] = len(g)
    except Exception as e:
        print(f"[load][WARN] web gasto_dane: {e}")
    try:
        men = _latest_raw("alerts_rss")
        if not men.empty:
            cols = [c for c in ("fecha", "titulo", "link", "feed") if c in men.columns]
            (WEBDATA / "menciones.json").write_text(
                men[cols].head(200).to_json(orient="records", force_ascii=False),
                encoding="utf-8",
            )
            out["menciones"] = min(len(men), 200)
    except Exception as e:
        print(f"[load][WARN] web menciones: {e}")
    try:
        occ = _latest_raw("medata_ocupacion_med")
        if not occ.empty:
            (WEBDATA / "ocupacion_hist.json").write_text(
                occ.head(500).to_json(orient="records", force_ascii=False),
                encoding="utf-8",
            )
            out["ocupacion_hist"] = min(len(occ), 500)
    except Exception as e:
        print(f"[load][WARN] web ocupacion_hist: {e}")
    try:
        tre = _latest_raw("google_trends")
        if not tre.empty:
            (WEBDATA / "trends.json").write_text(
                tre.tail(1000).to_json(orient="records", force_ascii=False),
                encoding="utf-8",
            )
            out["trends"] = min(len(tre), 1000)
    except Exception as e:
        print(f"[load][WARN] web trends: {e}")
    return out


def run():
    PROC.mkdir(parents=True, exist_ok=True)
    hist = PROC / "kpis_historico.csv"
    if not hist.exists():
        print("[load][SKIP] sin kpis_historico.csv, correr transform primero")
        return None
    con = sqlite3.connect(PROC / "bureau.sqlite")
    tables: dict = {}
    try:
        for p in sorted(PROC.glob("*.csv")):
            if p.name.startswith("kpis_202") and p.name != "kpis_historico.csv":
                continue  # snapshots diarios sueltos, no van a sqlite
            if p.name.endswith("_.csv"):
                print(f"[load][SKIP] artefacto {p.name}")
                continue
            t = export_csv_to_sqlite_parquet(p, con)
            if t:
                tables[t] = p.name
    finally:
        con.close()
    web = export_web_json()
    print(f"[load] sqlite tablas={sorted(tables)} web_json={web}")
    print(f"[load] {len(tables)} tablas -> bureau.sqlite + parquet + {len(web)} json")
    return PROC / "bureau.sqlite"


if __name__ == "__main__":
    run()
