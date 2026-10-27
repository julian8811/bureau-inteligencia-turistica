"""Socrata datos.gov.co — cableado real y probado (27-oct-2026), paginado (28-oct-2026).
- 7wm8-w5ad Extranjeros No Residentes por ciudad (Medellín filtro directo, max a_o=2026)
- 96sh-4v8d Entradas extranjeros por nacionalidad/año/mes (181k filas -> 4 páginas)
- gb6w-ynu4 Tráfico aéreo Origen-Destino (filtro destino=MDE / origen=MDE, EOH igual)
- efw5-jiej Salidas de colombianos por país destino/año/mes (93k filas)
Sin API key. Paginación $limit/$offset hasta agotar.
"""
import pandas as pd
from .base import save, paginate_socrata

def q(dataset: str, soql: dict) -> pd.DataFrame:
    return paginate_socrata(dataset, soql)

def run_medellin_no_residentes() -> pd.DataFrame:
    # Ciudad Medellín, orden reciente primero
    df = q("7wm8-w5ad", {"ciudad": "Medellín", "$order": "a_o DESC, mes DESC"})
    return save(df, "medellin_no_residentes")

def run_entradas_nacionalidad() -> pd.DataFrame:
    df = q("96sh-4v8d", {"$order": "a_o DESC"})
    return save(df, "entradas_nacionalidad")

def run_aereo_mde() -> pd.DataFrame:
    # Llegadas a MDE + salidas desde MDE (dos queries, se concatenan)
    sel = "a_o,n_mero_de_mes,origen,nombre_origen,ciudad_origen,pais_origen,destino,nombre_destino,ciudad_destino,pais_destino,pasajeros,tipo_vuelo"
    lleg = q("gb6w-ynu4", {"destino": "MDE", "$select": sel, "$order": "a_o DESC,n_mero_de_mes DESC"})
    sal = q("gb6w-ynu4", {"origen": "MDE", "$select": sel, "$order": "a_o DESC,n_mero_de_mes DESC"})
    lleg["sentido"] = "llegada"
    sal["sentido"] = "salida"
    df = pd.concat([lleg, sal], ignore_index=True) if not lleg.empty or not sal.empty else pd.DataFrame()
    # EOH también (regional): mismo esquema
    lleg_eoh = q("gb6w-ynu4", {"destino": "EOH", "$select": sel, "$order": "a_o DESC,n_mero_de_mes DESC"})
    if not lleg_eoh.empty:
        lleg_eoh["sentido"] = "llegada_eoh"
        df = pd.concat([df, lleg_eoh], ignore_index=True)
    return save(df, "aereo_mde_eoh")

def run_salidas_destino() -> pd.DataFrame:
    df = q("efw5-jiej", {"$order": "a_o DESC"})
    return save(df, "salidas_destino")

def run_ciudades_agregado() -> pd.DataFrame:
    """Todas las ciudades x año en UNA query agregada (evita paginar 524k filas)."""
    import requests
    try:
        r = requests.get("https://www.datos.gov.co/resource/7wm8-w5ad.json", params={
            "$select": "ciudad,a_o,sum(cant_extranjeros_no_residentes) as llegadas",
            "$group": "ciudad,a_o", "$order": "a_o DESC", "$limit": "50000"}, timeout=60)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
    except Exception as e:
        print(f"[socrata][WARN] ciudades_agregado: {e}")
        df = pd.DataFrame()
    return save(df, "ciudades_llegadas")

def run():
    return [run_medellin_no_residentes(), run_entradas_nacionalidad(), run_aereo_mde(), run_salidas_destino(), run_ciudades_agregado()]

if __name__ == "__main__":
    run()
