"""Eurostat avia_paoc — pasajeros aereos (conectividad emisores).

Tematica: vacacional/MICE — conectividad aerea UE + Espana (emisor clave).
Patron eurostat_tourism.py: filtros minimos geo+time contra
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>
Evidencia 29-oct-2026 (curl): avia_paoc sin filtros -> 413 (pide async);
con filtros geo=EU27_2020,ES + time=2023,2024 -> 200 con dato.
avia_par con los mismos filtros -> 404
"ERR_NOT_FOUND_4: AVIA_PAR (DATA_FLOW:ALL,1.0) is not available
for dissemination." Podado del daily 31-oct-2026 (S2/S3).
Si avia_paoc falla -> carry-forward via save_or_carry, nunca tumba el daily.
"""

import itertools

import pandas as pd
import requests

from .base import UA, save_or_carry

DATASETS = ["avia_paoc"]
GEOS = ["EU27_2020", "ES"]
TIMES = ["2023", "2024"]
COLUMNS = ["geo", "time", "passengers"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _parse_jsonstat(payload: dict) -> pd.DataFrame:
    """run() individual: parse JSON-stat {dimension, value, id, size} a filas geo/time."""
    try:
        dims = payload.get("dimension", {})
        ids = payload.get("id", [])
        sizes = payload.get("size", [])
        values = payload.get("value", {})
        if not ids or not sizes:
            return _empty()
        labels = {}
        for name in ids:
            cat = dims.get(name, {}).get("category", {})
            idx = cat.get("index", {})
            lab = cat.get("label", {})
            inv = {v: k for k, v in idx.items()}
            ordered = [inv.get(i, "") for i in range(sizes[ids.index(name)])]
            labels[name] = [lab.get(c, c) for c in ordered]
        recs = []
        for combo in itertools.product(*[range(s) for s in sizes]):
            flat = 0
            mult = 1
            for i in reversed(range(len(sizes))):
                flat += combo[i] * mult
                mult *= sizes[i]
            val = values.get(str(flat))
            row = {name: labels[name][combo[j]] for j, name in enumerate(ids)}
            recs.append(
                {
                    "geo": row.get("geo", ""),
                    "time": row.get("time", ""),
                    "passengers": val,
                }
            )
        return pd.DataFrame(recs).reindex(columns=COLUMNS)
    except Exception as e:
        print(f"[extract][WARN] eurostat_aviation parse: {e}")
        return _empty()


def run_pax(geos=None, times=None) -> pd.DataFrame:
    """run() individual: query minima geo+time a avia_paoc (unico dataset vivo)."""
    geos = geos or GEOS
    times = times or TIMES
    for dataset in DATASETS:
        params = [("format", "JSON"), ("lang", "en")]
        params += [("geo", g) for g in geos]
        params += [("time", t) for t in times]
        try:
            r = requests.get(
                f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}",
                params=params,
                headers=UA,
                timeout=30,
            )
            r.raise_for_status()
            df = _parse_jsonstat(r.json())
            print(f"[extract] eurostat {dataset}: {len(df)} filas")
            if not df.empty:
                return df
            print(f"[extract][WARN] eurostat {dataset}: 200 sin filas, pruebo siguiente")
        except Exception as e:
            print(f"[extract][WARN] eurostat {dataset}: {e}")
    return _empty()


def run():
    """run() agregador: guarda data/raw/<hoy>/eurostat_aviation.csv con carry-forward."""
    try:
        df = run_pax()
    except Exception as e:
        print(f"[extract][WARN] eurostat_aviation agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "eurostat_aviation", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] eurostat_aviation save: {e}")
        return []


if __name__ == "__main__":
    run()
