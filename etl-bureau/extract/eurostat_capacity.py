"""Eurostat tour_cap_nat — camas/plazas de los emisores (oferta benchmark).

Evidencia 28-oct-2026 (parent): dissemination API 200 OK con geo=ES&time=2023.
Filtros: geo EU27_2020+ES+DE+FR+IT, time 2023:2024.
Patron: eurostat_tourism.py (query minima geo+time, parse JSON-stat, carry-forward).
Nunca tumba el daily: todo try/except, timeout <=30s, sin nuevas dependencias.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

DATASET = "tour_cap_nat"
GEOS = ["EU27_2020", "ES", "DE", "FR", "IT"]
TIMES = ["2023", "2024"]
COLUMNS = ["geo", "time", "accomunit", "unit", "nace_r2", "value"]
TIMEOUT = 30


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _parse_jsonstat(payload: dict) -> pd.DataFrame:
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
                    "accomunit": row.get("accomunit", ""),
                    "unit": row.get("unit", ""),
                    "nace_r2": row.get("nace_r2", ""),
                    "value": val,
                }
            )
        out: pd.DataFrame = pd.DataFrame(recs).reindex(columns=COLUMNS)
        print(f"[extract] eurostat {DATASET}: {len(out)} filas con dato")
        return out
    except Exception as e:
        print(f"[extract][WARN] eurostat_capacity parse: {e}")
        return _empty()


def run_capacity(geos=None, times=None) -> pd.DataFrame:
    """run() individual: query minima geo+time al dataset tour_cap_nat."""
    geos = geos or GEOS
    times = times or TIMES
    params = [("format", "JSON"), ("lang", "en")]
    params += [("geo", g) for g in geos]
    params += [("time", t) for t in times]
    try:
        r = requests.get(
            f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{DATASET}",
            params=params,
            headers=UA,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        df = _parse_jsonstat(r.json())
        print(f"[extract] eurostat {DATASET}: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] eurostat {DATASET}: {e}")
        return _empty()


def run():
    """run() agregador: guarda data/raw/<hoy>/eurostat_capacity.csv con carry-forward."""
    try:
        df = run_capacity()
    except Exception as e:
        print(f"[extract][WARN] eurostat_capacity agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "eurostat_capacity", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] eurostat_capacity save: {e}")
        return []


if __name__ == "__main__":
    run()
