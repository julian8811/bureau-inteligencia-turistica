"""Load: Parquet + SQLite listo para Power BI (Get Data -> SQLite / Folder CSV)."""
from pathlib import Path
import sqlite3
import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"

def run():
    hist = PROC / "kpis_historico.csv"
    if not hist.exists():
        print("[load][SKIP] sin kpis_historico.csv, correr transform primero")
        return None
    df = pd.read_csv(hist)
    df.to_parquet(PROC / "kpis_historico.parquet", index=False)
    con = sqlite3.connect(PROC / "bureau.sqlite")
    df.to_sql("kpis_diario", con, if_exists="replace", index=False)
    con.close()
    print(f"[load] {len(df)} días -> bureau.sqlite:kpis_diario + parquet")
    return PROC / "bureau.sqlite"

if __name__ == "__main__":
    run()
