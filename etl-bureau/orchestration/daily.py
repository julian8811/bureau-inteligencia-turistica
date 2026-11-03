"""Orquestador diario: corre extract -> transform -> load. Nunca tumba todo por una fuente."""
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classify import llm_classify
from dashboard import build_html
from export import bureau_runner
from export import tableros_bureau_llm
from extract import (
    aerocivil_flota,
    aire_med,
    alerts_rss,
    avisos_viaje,
    bts_colombia,
    dane_egit,
    dane_ema,
    dane_ipc,
    eurostat_arrivals,
    eurostat_aviation,
    eurostat_capacity,
    eurostat_demanda,
    eurostat_tourism,
    festivos_co,
    fx_cop,
    gastronomia_nocturna,
    gated_icca,
    gdelt_marca,
    google_trends,
    ideam_clima,
    medata,
    metro_movilidad,
    openmeteo_ensemble,
    prensa_rss,
    rnt_antioquia,
    rnt_prestadores,
    seguridad_med,
    sisaire_amva,
    socrata_co,
    socrata_operaciones,
    terminales_med,
    trm_co,
    wikimedia_views,
)
from load import to_warehouse
from backend import writer as backend_writer
from report import redactar_informe
from report import publicar_pdfs
from export import publicar as publicar_tableros
from transform import kpis


def main():
    for step in (
        google_trends.run,
        socrata_co.run,
        socrata_operaciones.run,
        medata.run,
        dane_egit.run,
        dane_ema.run,
        dane_ipc.run,
        gdelt_marca.run,
        eurostat_tourism.run,
        alerts_rss.run,
        gated_icca.run,
        eurostat_aviation.run,
        eurostat_arrivals.run,
        trm_co.run,
        festivos_co.run,
        avisos_viaje.run,
        wikimedia_views.run,
        prensa_rss.run,
        rnt_prestadores.run,
        seguridad_med.run,
        metro_movilidad.run,  # solo Metro; terminales va por terminales_med
        ideam_clima.run,
        sisaire_amva.run,
        gastronomia_nocturna.run,
        terminales_med.run,  # canonico terminales -> pax_terminal_mes
        eurostat_capacity.run,
        eurostat_demanda.run,
        rnt_antioquia.run,
        aerocivil_flota.run,
        aire_med.run,
        bts_colombia.run,
        fx_cop.run,
        openmeteo_ensemble.run,
        llm_classify.run,
        kpis.run,
        to_warehouse.run,
        backend_writer.run,
        redactar_informe.run,
        publicar_pdfs.run,
        bureau_runner.run,  # piezas bureau_* ANTES del adapter y del publish
        tableros_bureau_llm.run,
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
