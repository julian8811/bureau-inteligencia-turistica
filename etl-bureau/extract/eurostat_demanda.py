"""Eurostat demanda — participacion/viajes de los emisores.

Prueba datasets en orden [tour_dem_ttot, tour_dem_toac, tour_dem_ttmd] con los
mismos filtros minimos (geo EU27_2020+ES+DE+FR+IT, time 2023:2024); se queda con
el primero que de 200 con dato.
Patron: eurostat_tourism.py (query minima geo+time, parse JSON-stat, carry-forward).
Nunca tumba el daily: todo try/except, timeout <=30s, sin nuevas dependencias.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

DATASETS = ["tour_dem_ttot", "tour_dem_toac", "tour_dem_ttmd"]
GEOS = ["EU27_2020", "ES", "DE", "FR", "IT"]
TIMES = ["2023", "2024"]
COLUMNS = ["geo", "time", "value", "dataset"]
TIMEOUT = 30


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _parse_jsonstat(payload: dict, dataset: str) -> pd.DataFrame:
    """Parse JSON-stat {dimension, value, id, size} a filas usando codigos (index keys)."""
    try:
        dims = payload.get("dimension", {})
        ids = payload.get("id", [])
        sizes = payload.get("size", [])
        values = payload.get("value", {})
        if not ids or not sizes:
            return _empty()
        codes = {}
        for name in ids:
            idx = dims.get(name, {}).get("category", {}).get("index", {})
            inv = {v: k for k, v in idx.items()}
            codes[name] = [inv.get(i, "") for i in range(sizes[ids.index(name)])]
        import itertools

        recs = []
        for combo in itertools.product(*[range(s) for s in sizes]):
            flat = 0
            mult = 1
            for i in reversed(range(len(sizes))):
                flat += combo[i] * mult
                mult *= sizes[i]
            val = values.get(str(flat))
            if val is None:
                continue
            row = {name: codes[name][combo[j]] for j, name in enumerate(ids)}
            recs.append(
                {
                    "geo": row.get("geo", ""),
                    "time": row.get("time", ""),
                    "value": val,
                    "dataset": dataset,
                }
            )
        df = pd.DataFrame(recs).reindex(columns=COLUMNS)
        print(f"[extract] eurostat {dataset}: {len(df)} filas con dato")
        return df
    except Exception as e:
        print(f"[extract][WARN] eurostat_demanda parse {dataset}: {e}")
        return _empty()


def run_dataset(dataset: str, geos=None, times=None) -> pd.DataFrame:
    """run() individual: query minima geo+time a un dataset de demanda."""
    geos = geos or GEOS
    times = times or TIMES
    params = [("format", "JSON"), ("lang", "en")]
    params += [("geo", g) for g in geos]
    params += [("time", t) for t in times]
    try:
        r = requests.get(
            f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}",
            params=params,
            headers=UA,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return _parse_jsonstat(r.json(), dataset)
    except Exception as e:
        print(f"[extract][WARN] eurostat {dataset}: {e}")
        return _empty()


def run():
    """run() agregador: primer dataset con 200+dato gana; guarda eurostat_demanda.csv."""
    df = _empty()
    try:
        for dataset in DATASETS:
            cand = run_dataset(dataset)
            if not cand.empty:
                df = cand
                print(f"[extract] eurostat_demanda: gana {dataset} ({len(df)} filas)")
                break
        if df.empty:
            print("[extract][WARN] eurostat_demanda: ningun dataset dio dato")
    except Exception as e:
        print(f"[extract][WARN] eurostat_demanda agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "eurostat_demanda", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] eurostat_demanda save: {e}")
        return []


if __name__ == "__main__":
    run()
