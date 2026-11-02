"""Orquestador diario: corre extract -> transform -> load. Nunca tumba todo por una fuente."""
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classify import llm_classify
from dashboard import build_html
from export import tableros_bureau_llm
from extract import (
    aerocivil_flota,
    aerodatabox_mde,
    aire_med,
    alerts_rss,
    dane_egit,
    dane_ema,
    eurostat_arrivals,
    eurostat_aviation,
    eurostat_capacity,
    eurostat_demanda,
    eurostat_tourism,
    festivos_co,
    gastronomia_nocturna,
    gated_amadeus,
    gated_brand24,
    gated_flightpowers,
    gated_icca,
    gdelt_marca,
    google_trends,
    ideam_clima,
    medata,
    metro_movilidad,
    opensky_mde,
    prensa_rss,
    rnt_antioquia,
    rnt_prestadores,
    seguridad_med,
    socrata_co,
    terminales_med,
    ticketmaster_eventos,
    trm_co,
    un_wb_arrivals,
    wb_departures,
    wb_receipts,
    wikimedia_views,
)
from load import to_warehouse
from extract.socrata_migrantes import run as socrata_migrantes_run
from extract.socrata_operaciones import run as socrata_operaciones_run
from extract.opentripmap_med import run as opentripmap_med_run
from backend import writer as backend_writer
from report import redactar_informe
from report import publicar_pdfs
from export import publicar as publicar_tableros
from transform import kpis


def main():
    for step in (
        google_trends.run,
        socrata_co.run,
        socrata_operaciones_run,
        socrata_migrantes_run,
        medata.run,
        dane_egit.run,
        dane_ema.run,
        gdelt_marca.run,
        un_wb_arrivals.run,
        eurostat_tourism.run,
        alerts_rss.run,
        gated_icca.run,
        gated_amadeus.run,
        gated_brand24.run,
        gated_flightpowers.run,
        gated_flightpowers.run_hotels,
        aerodatabox_mde.run,
        wb_receipts.run,
        eurostat_aviation.run,
        eurostat_arrivals.run,
        trm_co.run,
        festivos_co.run,
        wikimedia_views.run,
        prensa_rss.run,
        rnt_prestadores.run,
        seguridad_med.run,
        metro_movilidad.run,  # solo Metro; terminales va por terminales_med
        ideam_clima.run,
        opensky_mde.run,
        gastronomia_nocturna.run,
        ticketmaster_eventos.run,
        opentripmap_med_run,
        terminales_med.run,  # canonico terminales -> pax_terminal_mes
        wb_departures.run,
        eurostat_capacity.run,
        eurostat_demanda.run,
        rnt_antioquia.run,
        aerocivil_flota.run,
        aire_med.run,
        llm_classify.run,
        kpis.run,
        to_warehouse.run,
        backend_writer.run,
        redactar_informe.run,
        publicar_pdfs.run,
        tableros_bureau_llm.run,  # adapter ANTES del publish: genera export/tableros_bureau/* que push/actualizar suben
        publicar_tableros.push_export,
        publicar_tableros.actualizar_tableros,
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
