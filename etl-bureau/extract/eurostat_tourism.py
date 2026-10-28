"""Eurostat tour_occ_ninat — noches en alojamientos turisticos (natives/inbound).

Evidencia 28-oct-2026: la dissemination API dio 500 con dims provisorias;
se fijan filtros minimos (geo + time) segun la API estable:
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tour_occ_ninat
Si la API vuelve a fallar -> carry-forward via save_or_carry, nunca tumba el daily.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

DATASET = "tour_occ_ninat"
GEOS = ["ES", "FR", "DE"]
TIMES = ["2023", "2024"]
COLUMNS = ["geo", "time", "nights"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _parse_jsonstat(payload: dict) -> pd.DataFrame:
    """run() individual: parse JSON-stat {dimension, value, id, size} a filas."""
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
        import itertools

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
                    "nights": val,
                }
            )
        return pd.DataFrame(recs).reindex(columns=COLUMNS)
    except Exception as e:
        print(f"[extract][WARN] eurostat parse: {e}")
        return _empty()


def run_nights(geos=None, times=None) -> pd.DataFrame:
    """run() individual: query minima geo+time al dataset tour_occ_ninat."""
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
            timeout=90,
        )
        r.raise_for_status()
        df = _parse_jsonstat(r.json())
        print(f"[extract] eurostat {DATASET}: {len(df)} filas")
        return df
    except Exception as e:
        print(f"[extract][WARN] eurostat {DATASET}: {e}")
        return _empty()


def run():
    """run() agregador: guarda data/raw/<hoy>/eurostat_tourism.csv con carry-forward."""
    try:
        df = run_nights()
    except Exception as e:
        print(f"[extract][WARN] eurostat agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "eurostat_tourism", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] eurostat save: {e}")
        return []


if __name__ == "__main__":
    run()
