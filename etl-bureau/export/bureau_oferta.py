"""Oferta y territorio -> export/tableros_bureau/oferta_territorio_2025_2026.json.

Lee RAW de data/raw/<fecha>/ (por defecto 2026-11-02) y publica el JSON de
oferta para `alimentar_bureau.py` (repo tableros-bureau).

Solo stdlib + pandas. Lectura defensiva: archivo ausente o vacio ->
{"estado": "skip", "motivo": ...}, exit 0, nunca tumba.
"""

import contextlib
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # etl-bureau/
RAW_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw" / "2026-11-02"
OUT = Path(__file__).resolve().parent / "tableros_bureau" / "oferta_territorio_2025_2026.json"

ID = "bureau-oferta"
VENTANA = "2025-2026"
FUENTE = "RNT + MeData + DANE-EGIT (raw 2026-11-02)"

RNT_FILES = ["rnt_antioquia.csv", "rnt_prestadores.csv"]
REQUIRED_FILES = [
    "medata_tarifa_zona.csv",
    "medata_ocupacion_zonas.csv",
    "medata_eventos_uplift.csv",
    "dane_egit_turismo_interno.csv",
]
EVENTOS = ["feria", "mitad", "moda", "receso", "santa", "tex"]
OCC_FILES = {e: f"medata_occ_{e}.csv" for e in EVENTOS}

TRIM_RE = re.compile(r"^([IV]+)\s*-\s*(\d{4})$")
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}


def hoy():
    return datetime.date.today().isoformat()


def skip(motivo):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "id": ID,
                "generado": hoy(),
                "ventana": VENTANA,
                "fuente": FUENTE,
                "serie": {},
                "estado": "skip",
                "motivo": motivo,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_csv(name):
    """Devuelve DataFrame o None si ausente/vacio/ilegible."""
    p = RAW_DIR / name
    if not p.is_file():
        return None
    try:
        df = pd.read_csv(p, encoding="utf-8")
    except Exception:
        return None
    if df.empty:
        return None
    return df


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return v if v == v else 0.0  # NaN -> 0


def build_rnt(dfs):
    df = pd.concat(dfs, ignore_index=True)
    municipios = [str(m).strip() for m in df["municipio"].tolist()]
    categorias = [str(c).strip() for c in df["categoria"].tolist()]
    habs = [_num(x) for x in df["habitaciones"].tolist()]
    camas = [_num(x) for x in df["camas"].tolist()]
    top = Counter(municipios).most_common(8)
    agg = {}
    for cat, h, c in zip(categorias, habs, camas, strict=True):
        e = agg.setdefault(cat, [0, 0.0, 0.0])
        e[0] += 1
        e[1] += h
        e[2] += c
    por_cat = sorted(agg.items(), key=lambda kv: kv[1][0], reverse=True)
    return {
        "prestadores": int(len(df)),
        "habitaciones": int(sum(habs)),
        "camas": int(sum(camas)),
        "top_municipios": [
            {"municipio": m, "prestadores": int(n)} for m, n in top
        ],
        "por_categoria": [
            {
                "categoria": cat,
                "prestadores": int(v[0]),
                "habitaciones": int(v[1]),
                "camas": int(v[2]),
            }
            for cat, v in por_cat
        ],
    }


def build_tarifa_zona(df):
    df = df.copy()
    df["tar_periodo"] = pd.to_numeric(df["tar_periodo"], errors="coerce")
    df["tar_valor"] = pd.to_numeric(df["tar_valor"], errors="coerce")
    df = df.dropna(subset=["tar_periodo", "tar_valor"])
    df["tar_zona"] = df["tar_zona"].astype(str).str.strip()
    idx = df.groupby("tar_zona")["tar_periodo"].idxmax()
    latest = df.loc[idx].sort_values("tar_zona")
    return [
        {"zona": r["tar_zona"], "periodo": int(r["tar_periodo"]), "valor": float(r["tar_valor"])}
        for r in latest.to_dict(orient="records")
    ]


def build_ocupacion_zonas(df):
    df = df.copy()
    df["ocu_zona"] = df["ocu_zona"].astype(str).str.strip()
    return [
        {
            "zona": r["ocu_zona"],
            "prom": float(r["ocu_prom"]),
            "n_meses": int(r["n_meses"]),
        }
        for r in df.sort_values("ocu_zona").to_dict(orient="records")
    ]


def build_temporadas(uplift_df, occ_dfs):
    up = uplift_df.copy()
    up["evento"] = up["evento"].astype(str).str.strip().str.lower()
    up = up.set_index("evento")
    bloques = []
    for e in EVENTOS:
        occ = occ_dfs[e].copy()
        occ["ocu_valor"] = pd.to_numeric(occ["ocu_valor"], errors="coerce")
        vals = occ["ocu_valor"].dropna()
        row = up.loc[e] if e in up.index else None
        bloques.append(
            {
                "evento": e,
                "occ_evento": float(row["occ_evento"]) if row is not None else None,
                "occ_base": float(row["occ_base"]) if row is not None else None,
                "uplift_pp": float(row["uplift_pp"]) if row is not None else None,
                "n_periodos": int(len(vals)),
                "occ_prom": round(float(vals.mean()), 2) if len(vals) else None,
            }
        )
    return bloques


def trim_key(t):
    m = TRIM_RE.match(str(t).strip())
    if not m:
        return None
    return (int(m.group(2)), ROMAN[m.group(1)])


def build_turismo_interno(df, cap=5):
    df = df.copy()
    df["concepto"] = df["concepto"].astype(str).str.strip()
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df[df["trimestre"].astype(str).str.strip().str.match(TRIM_RE, na=False)]
    df = df.dropna(subset=["valor"])
    counts = df["concepto"].value_counts()
    conceptos = list(counts.head(cap).index)
    serie = {}
    for c in conceptos:
        sub = df[df["concepto"] == c].copy()
        # El raw repite concepto por trimestre (total + desagregados); la
        # primera fila de cada trimestre es el total nacional.
        sub = sub.drop_duplicates(subset=["trimestre"], keep="first")
        sub["orden"] = sub["trimestre"].map(trim_key)
        sub = sub.dropna(subset=["orden"]).sort_values("orden")
        serie[c] = [
            {"trimestre": str(r["trimestre"]).strip(), "valor": float(r["valor"])}
            for r in sub.to_dict(orient="records")
        ]
    return {"conceptos": conceptos, "serie": serie}


def main():
    try:
        faltantes = [f for f in REQUIRED_FILES if (RAW_DIR / f).is_file() is False]
        faltantes += [
            f"medata_occ_{e}.csv" for e in EVENTOS if not (RAW_DIR / OCC_FILES[e]).is_file()
        ]
        rnt_dfs = []
        for f in RNT_FILES:
            df = load_csv(f)
            if df is not None:
                rnt_dfs.append(df)
        if not rnt_dfs:
            faltantes = RNT_FILES + faltantes

        vacios = []
        for f in REQUIRED_FILES + [OCC_FILES[e] for e in EVENTOS]:
            p = RAW_DIR / f
            if p.is_file() and p.stat().st_size == 0:
                vacios.append(f)
        if faltantes or vacios:
            motivos = []
            if faltantes:
                motivos.append("ausentes: " + ", ".join(faltantes))
            if vacios:
                motivos.append("vacios: " + ", ".join(vacios))
            skip("RAW " + "; ".join(motivos))
            return 0

        tarifa = load_csv("medata_tarifa_zona.csv")
        ocup = load_csv("medata_ocupacion_zonas.csv")
        uplift = load_csv("medata_eventos_uplift.csv")
        turismo = load_csv("dane_egit_turismo_interno.csv")
        occ_dfs = {e: load_csv(OCC_FILES[e]) for e in EVENTOS}
        todo = [tarifa, ocup, uplift, turismo] + list(occ_dfs.values())
        if any(d is None or d.empty for d in todo):
            skip("RAW ilegible o sin filas en uno o mas archivos requeridos")
            return 0

        serie = {
            "rnt": build_rnt(rnt_dfs),
            "tarifa_zona": build_tarifa_zona(tarifa),
            "ocupacion_zonas": build_ocupacion_zonas(ocup),
            "temporadas": build_temporadas(uplift, occ_dfs),
            "turismo_interno": build_turismo_interno(turismo),
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(
            json.dumps(
                {
                    "id": ID,
                    "generado": hoy(),
                    "ventana": VENTANA,
                    "fuente": FUENTE,
                    "serie": serie,
                    "estado": "ok",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return 0
    except Exception as ex:  # defensivo: nunca tumbar el pipeline
        with contextlib.suppress(Exception):
            skip(f"excepcion: {type(ex).__name__}: {ex}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
