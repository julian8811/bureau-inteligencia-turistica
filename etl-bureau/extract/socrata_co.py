"""Socrata datos.gov.co — cableado real y probado (27-oct-2026).
- 7wm8-w5ad Extranjeros No Residentes por ciudad (Medellín filtro directo, max a_o=2026)
- 96sh-4v8d Entradas extranjeros por nacionalidad/año/mes
- gb6w-ynu4 Tráfico aéreo Origen-Destino (filtro destino=MDE / origen=MDE, EOH igual)
Sin API key, límite generoso. Incremental: trae últimos 24 meses por defecto.
"""
import requests
import pandas as pd
from .base import save

BASE = "https://www.datos.gov.co/resource"
APP_TOKEN = None  # opcional: poner en env SOCRATA_APP_TOKEN para mayor cuota
TIMEOUT = 30

def q(dataset: str, soql: dict) -> pd.DataFrame:
    try:
        r = requests.get(f"{BASE}/{dataset}.json", params=soql, timeout=TIMEOUT)
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except Exception as e:
        print(f"[socrata][WARN] {dataset}: {e}")
        return pd.DataFrame()

def run_medellin_no_residentes(limit: int = 50000) -> pd.DataFrame:
    # Ciudad Medellín, orden reciente primero
    df = q("7wm8-w5ad", {
        "ciudad": "Medellín",
        "$order": "a_o DESC, mes DESC",
        "$limit": str(limit),
    })
    return save(df, "medellin_no_residentes")

def run_entradas_nacionalidad(limit: int = 50000) -> pd.DataFrame:
    df = q("96sh-4v8d", {"$order": "a_o DESC", "$limit": str(limit)})
    return save(df, "entradas_nacionalidad")

def run_aereo_mde(limit: int = 50000) -> pd.DataFrame:
    # Llegadas a MDE + salidas desde MDE (dos queries, se concatenan)
    sel = "a_o,n_mero_de_mes,origen,nombre_origen,ciudad_origen,pais_origen,destino,nombre_destino,ciudad_destino,pais_destino,pasajeros,tipo_vuelo"
    lleg = q("gb6w-ynu4", {"destino": "MDE", "$select": sel, "$order": "a_o DESC,n_mero_de_mes DESC", "$limit": str(limit)})
    sal = q("gb6w-ynu4", {"origen": "MDE", "$select": sel, "$order": "a_o DESC,n_mero_de_mes DESC", "$limit": str(limit)})
    lleg["sentido"] = "llegada"
    sal["sentido"] = "salida"
    df = pd.concat([lleg, sal], ignore_index=True) if not lleg.empty or not sal.empty else pd.DataFrame()
    # EOH también (regional): mismo esquema
    lleg_eoh = q("gb6w-ynu4", {"destino": "EOH", "$select": sel, "$order": "a_o DESC,n_mero_de_mes DESC", "$limit": "5000"})
    if not lleg_eoh.empty:
        lleg_eoh["sentido"] = "llegada_eoh"
        df = pd.concat([df, lleg_eoh], ignore_index=True)
    return save(df, "aereo_mde_eoh")

def run():
    return [run_medellin_no_residentes(), run_entradas_nacionalidad(), run_aereo_mde()]

if __name__ == "__main__":
    run()
