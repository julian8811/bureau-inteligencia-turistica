"""OECD tourism — inbound/key indicators via SDMX-JSON (api.sdmx.oecd.org v1).

Evidencia 28-oct-2026: el endpoint provisorio dio 500. Se fijaron los
dataflows correctos contra el registry vivo:
  agency OECD.CFE.TOU, DSD_TOURISM_INTER@DF_INBOUND v1.1 (inbound),
  agency OECD.CFE.TOU, DSD_TOURISM_KEY@DF_KEY_IND_PC v1.0 (key indicators).
Hallazgo: ambos estan marcados NonProductionDataflow=true y devuelven
0 series (metadata sin dato disseminado). -> SKIP honesto con mensaje y
carry-forward via save_or_carry, sin tumbar el daily. Si la OCDE publica
dato a futuro, el query ya queda cableado y fluye solo.
"""

import pandas as pd
import requests

from .base import UA, save_or_carry

AGENCY = "OECD.CFE.TOU"
FLOWS = [
    ("DSD_TOURISM_INTER@DF_INBOUND", "1.1"),
    ("DSD_TOURISM_KEY@DF_KEY_IND_PC", "1.0"),
]
REF_AREAS = ["COL", "ESP", "USA", "FRA", "MEX"]
YEAR = "2024"
COLUMNS = ["dataflow", "key", "time", "value"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUMNS})


def _parse_sdmx(payload: dict, flow: str) -> pd.DataFrame:
    """Mapea series JSON-stat SDMX a filas usando el bloque structures."""
    try:
        data = payload.get("data", {})
        sets = data.get("dataSets", [])
        structs = data.get("structures", [])
        if not sets or not structs:
            return _empty()
        st = structs[0]
        dims = st.get("dimensions", {})
        series_dims = dims.get("series", []) if isinstance(dims, dict) else []
        obs_dims = dims.get("observation", []) if isinstance(dims, dict) else []
        times = [
            v.get("id") for v in (obs_dims[0].get("values", []) if obs_dims else [])
        ]
        recs = []
        for skey, ser in sets[0].get("series", {}).items():
            parts = skey.split(":")
            labels = []
            for i, p in enumerate(parts):
                vals = series_dims[i].get("values", []) if i < len(series_dims) else []
                try:
                    labels.append(
                        f"{series_dims[i].get('id') if i < len(series_dims) else i}={vals[int(p)].get('id')}"
                    )
                except (ValueError, IndexError):
                    labels.append(p)
            for tkey, oval in ser.get("observations", {}).items():
                try:
                    t = times[int(tkey)]
                except (ValueError, IndexError):
                    t = tkey
                val = oval[0] if isinstance(oval, list) else oval
                recs.append(
                    {"dataflow": flow, "key": "|".join(labels), "time": t, "value": val}
                )
        return pd.DataFrame(recs).reindex(columns=COLUMNS)
    except Exception as e:
        print(f"[extract][WARN] oecd parse {flow}: {e}")
        return _empty()


def run_dataflow(flow: str, version: str) -> pd.DataFrame:
    """run() individual: un dataflow OECD.CFE.TOU con key REF_AREA y anio acotado."""
    frames = []
    for ref in REF_AREAS:
        flow_enc = flow.replace("@", "%40")
        url = f"https://sdmx.oecd.org/public/rest/v1/data/{AGENCY},{flow_enc},{version}/{ref}......."
        try:
            r = requests.get(
                url,
                params={
                    "startPeriod": YEAR,
                    "endPeriod": YEAR,
                    "dimensionAtObservation": "AllDimensions",
                },
                headers={**UA, "Accept": "application/vnd.sdmx.data+json"},
                timeout=60,
            )
            r.raise_for_status()
            got = _parse_sdmx(r.json(), flow)
            if not got.empty:
                frames.append(got)
        except Exception as e:
            print(f"[extract][WARN] oecd {flow} {ref}: {e}")
    df = pd.concat(frames, ignore_index=True) if frames else _empty()
    print(f"[extract] oecd {flow}: {len(df)} filas")
    return df


def run():
    """run() agregador: prueba dataflows en orden; SKIP honesto si ninguno trae dato."""
    df = _empty()
    try:
        for flow, version in FLOWS:
            got = run_dataflow(flow, version)
            if not got.empty:
                df = got
                break
        if df.empty:
            print(
                "[gated][SKIP] oecd_tourism sin dato SDMX estable"
                " (flows NonProductionDataflow=true, 0 series) -> skip con carry-forward"
            )
    except Exception as e:
        print(f"[extract][WARN] oecd agregador: {e}")
        df = _empty()
    try:
        return [save_or_carry(df, "oecd_tourism", COLUMNS)]
    except Exception as e:
        print(f"[extract][WARN] oecd save: {e}")
        return []


if __name__ == "__main__":
    run()
