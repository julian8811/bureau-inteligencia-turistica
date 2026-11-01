"""MEData Medellín — CSVs directos del portal de datos abiertos de la Alcaldía.
Hallazgo 28-oct: portal vivo pero series de turismo congeladas en 2023 (SITUR dejó de alimentar).
Uso: baseline histórico (ocupación, tarifa, PITS, llegadas MDE por país) para estacionalidad y
benchmarks. Lo fresco diario sigue viniendo de Socrata nacional + DANE.
Descarga liviana (<1MB total), con reintento https->http.
"""
import requests
import pandas as pd
from .base import save, UA

FILES = {
    # nombre_local: url_csv
    "medata_ocupacion_med": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000201/porcentaje_ocupacion_hotelera_mensual_de_medellin.csv",
    "medata_ocupacion_zona": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000202/porcentaje_ocupacion_hotelera_mensual_por_zona.csv",
    "medata_tarifa_med": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000209/tarifa_promedio_mensual_en_pesos_colombianos.csv",
    "medata_tarifa_zona": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000210/tarifa_promedio_mensual_por_zona_en_pesos_colombianos.csv",
    "medata_extranjeros_pais_mde": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000194/llegada_mensual_de_extranjeros_por_pais_de_residencia_por_punto_migratorio.csv",
    "medata_pax_int_origen": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000195/llegada_mensual_pasajeros_aeropuerto_de_origen_internacional.csv",
    "medata_pits": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000206/registro_de_visitantes_atendidos_en_los_pits.csv",
    "medata_sitios_interes": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000193/ingreso_mensual_de_visitantes_a_sitios_de_interes.csv",
    "medata_mig_mde": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000188/ingreso_mensual_de_extranjeros_y_colombianos_por_punto_migratorio_jose_maria_cordova.csv",
    "medata_travel_metrics": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000385/metricas_interaccion_medellin_travel.csv",
    # eventos: URLs verificadas del catálogo (uplift por evento)
    "medata_occ_feria": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000200/porcentaje_ocupacion_hotelera_feria_de_flores.csv",
    "medata_occ_moda": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000198/porcentaje_ocupacion_hotelera_colombiamoda.csv",
    "medata_occ_tex": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000199/porcentaje_ocupacion_hotelera_colombiatex.csv",
    "medata_occ_santa": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000203/porcentaje_ocupacion_hotelera_vacaciones_semana_santa.csv",
    "medata_occ_mitad": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000204/porcentaje_ocupacion_hotelera_vacaciones_mitad_de_ano.csv",
    "medata_occ_receso": "https://medata.app.medellin.gov.co/sites/default/files/distribution/1-010-04-000205/porcentaje_ocupacion_hotelera_vacaciones_receso_escolar.csv",
}

def fetch(url: str) -> pd.DataFrame:
    for u in (url, url.replace("https://", "http://")):
        try:
            r = requests.get(u, headers=UA, timeout=60)
            if r.status_code == 200 and len(r.content) > 100:
                from io import StringIO
                return pd.read_csv(StringIO(r.text))
        except Exception as e:
            print(f"[medata][WARN] {u}: {e}")
    return pd.DataFrame()

def shrink_travel_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """63MB de hits -> resumen mensual (el portal está congelado en 2023, solo sirve de baseline)."""
    try:
        df["mes"] = df["med_fecha"].astype(str).str.slice(0, 7)
        g = df.groupby("mes").agg(
            visitas=("med_visitas", "sum"), usuarios=("med_usuarios", "sum"), hits=("med_hits", "sum"))
        g["top_pais"] = df.groupby("mes")["med_pais"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else "")
        g["top_ruta"] = df.groupby("mes")["med_rutapaginadestino"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else "")
        return g.reset_index()
    except Exception as e:
        print(f"[medata][WARN] shrink travel_metrics: {e}")
        return df.head(0)

def run():
    outs = []
    for name, url in FILES.items():
        try:
            df = fetch(url)
            if name == "medata_travel_metrics" and not df.empty:
                df = shrink_travel_metrics(df)
            outs.append(save(df, name))
        except Exception as e:
            print(f"[medata][WARN] {name}: {e}")
            outs.append(save(pd.DataFrame(), name))
    return outs

if __name__ == "__main__":
    run()
