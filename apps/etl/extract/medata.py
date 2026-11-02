"""MEData Medellín — CSVs directos del portal de datos abiertos de la Alcaldía.
Hallazgo 28-oct: portal vivo pero series de turismo congeladas en 2023 (SITUR dejó de alimentar).
Uso: baseline histórico (ocupación, tarifa, PITS, llegadas MDE por país) para estacionalidad y
benchmarks. Lo fresco diario sigue viniendo de Socrata nacional + DANE.
Descarga liviana (<1MB total), con reintento https->http.

Fase 2 (T4 S1-S3, 2026-11-01): portal re-verificado sin datasets nuevos sin key
(CKAN apagado: /api/3/action -> 404; solo CSVs Drupal directos; serie fresca
máxima 202310). SKIP honesto: sin URLs nuevas inventadas. Cobertura extra vía
derivados locales: medata_pits_mensual (PITS por periodo), medata_ocupacion_zonas
(ranking zonas) y medata_eventos_uplift (6 eventos vs base). Jamás levanta.
"""
import requests
import pandas as pd
from .base import save, save_or_carry, UA

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

def build_pits_mensual(df: pd.DataFrame) -> pd.DataFrame:
    """PITS crudo -> agregado por periodo: visitas totales + puntos activos.
    pit_totalvisitas -1 = sin dato -> cuenta como 0 (no resta). Vacío -> vacío."""
    try:
        if df.empty or not {"pit_periodo", "pit_totalvisitas", "pit_nombre"} <= set(df.columns):
            return pd.DataFrame()
        d = df.copy()  # type: ignore[assignment]
        d["_v"] = pd.to_numeric(d["pit_totalvisitas"], errors="coerce").fillna(0)  # type: ignore[call-overload]
        d["_v"] = d["_v"].clip(lower=0)  # type: ignore[attr-defined]
        periods = sorted(d["pit_periodo"].dropna().unique().tolist())  # type: ignore[attr-defined]
        rows: list = []
        for p in periods:
            sub = d[d["pit_periodo"] == p]  # type: ignore[assignment]
            act = sub[sub["_v"] > 0]["pit_nombre"].dropna().unique()  # type: ignore[attr-defined]
            rows.append({"pit_periodo": p,
                         "visitas_total": int(sub["_v"].sum()),  # type: ignore[attr-defined]
                         "puntos_activos": int(len(act))})
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"[medata][WARN] build_pits_mensual: {e}")
        return pd.DataFrame()


def build_zonas_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Ocupación por zona -> ranking: ocupación promedio + meses con dato por zona."""
    try:
        if df.empty or not {"ocu_periodo", "ocu_valor", "ocu_zona"} <= set(df.columns):
            return pd.DataFrame()
        d = df.copy()  # type: ignore[assignment]
        d["_v"] = pd.to_numeric(d["ocu_valor"], errors="coerce")  # type: ignore[call-overload]
        d = d.dropna(subset=["_v"])  # type: ignore[assignment]
        if d.empty:  # type: ignore[attr-defined]
            return pd.DataFrame()
        zonas = sorted(d["ocu_zona"].dropna().unique().tolist())  # type: ignore[attr-defined]
        rows = []
        for z in zonas:
            sub = d[d["ocu_zona"] == z]  # type: ignore[assignment]
            rows.append({"ocu_zona": z,
                         "ocu_prom": round(float(sub["_v"].mean()), 2),  # type: ignore[attr-defined]
                         "n_meses": int(sub["_v"].count())})  # type: ignore[attr-defined]
        out = pd.DataFrame(rows)
        return out.sort_values("ocu_prom", ascending=False).reset_index(drop=True) if not out.empty else out  # type: ignore[attr-defined]
    except Exception as e:
        print(f"[medata][WARN] build_zonas_ranking: {e}")
        return pd.DataFrame()


def build_eventos_uplift(frames: dict) -> pd.DataFrame:
    """Dict {evento: df_ocupa} + clave 'base' -> uplift pp promedio por evento.
    Sin 'base' o sin eventos -> vacío (SKIP honesto, la agenda fresca no existe)."""
    try:
        base = frames.get("base")
        if base is None or base.empty or "ocu_valor" not in base.columns:  # type: ignore[attr-defined]
            return pd.DataFrame()
        bv = float(pd.to_numeric(base["ocu_valor"], errors="coerce").dropna().mean())  # type: ignore[call-overload,attr-defined]
        rows: list = []
        for tag, f_ in frames.items():
            if tag == "base" or f_.empty or "ocu_valor" not in f_.columns:  # type: ignore[attr-defined]
                continue
            ev = float(pd.to_numeric(f_["ocu_valor"], errors="coerce").dropna().mean())  # type: ignore[call-overload,attr-defined]
            rows.append({"evento": tag, "occ_evento": round(ev, 2),
                         "occ_base": round(bv, 2), "uplift_pp": round(ev - bv, 2)})
        out = pd.DataFrame(rows)
        return out.sort_values("uplift_pp", ascending=False).reset_index(drop=True) if not out.empty else out
    except Exception as e:
        print(f"[medata][WARN] build_eventos_uplift: {e}")
        return pd.DataFrame()


def run():
    outs = []
    frames: dict = {}
    for name, url in FILES.items():
        try:
            df = fetch(url)
            if name == "medata_travel_metrics" and not df.empty:
                df = shrink_travel_metrics(df)
            if name in ("medata_ocupacion_med", "medata_ocupacion_zona",
                        "medata_pits", "medata_occ_feria", "medata_occ_moda",
                        "medata_occ_tex", "medata_occ_santa", "medata_occ_mitad",
                        "medata_occ_receso"):
                frames[name] = df
            outs.append(save(df, name))
        except Exception as e:
            print(f"[medata][WARN] {name}: {e}")
            outs.append(save(pd.DataFrame(), name))
    # Fase 2: derivados locales (más zonas/categorías), cada uno con su try/except.
    try:
        outs.append(save_or_carry(build_pits_mensual(frames.get("medata_pits", pd.DataFrame())),
                                  "medata_pits_mensual"))
    except Exception as e:
        print(f"[medata][SKIP] medata_pits_mensual: {e}")
    try:
        outs.append(save_or_carry(build_zonas_ranking(frames.get("medata_ocupacion_zona", pd.DataFrame())),
                                  "medata_ocupacion_zonas"))
    except Exception as e:
        print(f"[medata][SKIP] medata_ocupacion_zonas: {e}")
    try:
        ev = {"base": frames.get("medata_ocupacion_med", pd.DataFrame())}
        for name, tag in (("medata_occ_feria", "feria"), ("medata_occ_moda", "moda"),
                          ("medata_occ_tex", "tex"), ("medata_occ_santa", "santa"),
                          ("medata_occ_mitad", "mitad"), ("medata_occ_receso", "receso")):
            ev[tag] = frames.get(name, pd.DataFrame())
        outs.append(save_or_carry(build_eventos_uplift(ev), "medata_eventos_uplift"))
    except Exception as e:
        print(f"[medata][SKIP] medata_eventos_uplift: {e}")
    return outs

if __name__ == "__main__":
    run()
