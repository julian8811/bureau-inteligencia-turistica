"""Orquestador diario: corre extract -> transform -> load. Nunca tumba todo por una fuente."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract import google_trends, oficiales_co, alerts_rss
from transform import kpis
from load import to_warehouse

def main():
    for step in (google_trends.run, oficiales_co.run, alerts_rss.run, kpis.run, to_warehouse.run):
        try:
            step()
        except Exception:
            print(f"[daily][ERROR] {step.__module__}.{step.__name__}")
            traceback.print_exc()
    print("[daily] OK")

if __name__ == "__main__":
    main()
