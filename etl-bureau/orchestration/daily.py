"""Orquestador diario: corre extract -> transform -> load. Nunca tumba todo por una fuente."""
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard import build_html
from extract import (
    alerts_rss,
    dane_egit,
    eurostat_tourism,
    gated_amadeus,
    gated_brand24,
    gated_icca,
    gdelt_marca,
    google_trends,
    medata,
    oecd_tourism,
    socrata_co,
    un_wb_arrivals,
    wttc_eir,
)
from load import to_warehouse
from transform import kpis


def main():
    for step in (
        google_trends.run,
        socrata_co.run,
        medata.run,
        dane_egit.run,
        gdelt_marca.run,
        un_wb_arrivals.run,
        eurostat_tourism.run,
        oecd_tourism.run,
        wttc_eir.run,
        alerts_rss.run,
        gated_amadeus.run,
        gated_brand24.run,
        gated_icca.run,
        kpis.run,
        to_warehouse.run,
        build_html.run,
    ):
        try:
            step()
        except Exception:
            print(f"[daily][ERROR] {step.__module__}.{step.__name__}")
            traceback.print_exc()
    print("[daily] OK")

if __name__ == "__main__":
    main()
