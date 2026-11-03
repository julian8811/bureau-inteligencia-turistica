"""Oferta y territorio -> export/tableros_bureau/oferta_territorio_2025_2026.json.

Lee RAW de data/raw/<fecha>/ (por defecto 2026-11-02) y publica el JSON de
oferta para `alimentar_bureau.py` (repo tableros-bureau).

Solo stdlib + pandas. Lectura defensiva: archivo ausente o vacio ->
{"estado": "skip", "motivo": ...}, exit 0, nunca tumba.

Fuentes retiradas 2026-11-02 (sin datos actuales, ver `retiradas` en el
payload): tarifa por zona (a 2023-03), ocupacion por zonas (agregado sin
fecha), uplift de temporadas (datos 2015-2021).
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
RAW_DIR = ROOT / "data" / "raw"
OUT = Path(__file__).resolve().parent / "tableros_bureau" / "oferta_territorio_2025_2026.json"

ID = "bureau-oferta"
VENTANA = "2025-2026"
FUENTE = "RNT + DANE-EGIT (raw 2026-11-02)"

RNT_FILES = ["rnt_antioquia.csv", "rnt_prestadores.csv"]
REQUIRED_FILES = ["dane_egit_turismo_interno.csv"]

RETIRADAS = [
    "medata_tarifa_zona.csv: corta en 2023-03",
    "medata_ocupacion_zonas.csv: agregado sin fecha",
    "medata_occ_*.csv + medata_eventos_uplift.csv: datos 2015-2021",
]

TRIM_RE = re.compile(r"^([IV]+)\s*-\s*(\d{4})$")
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}
MESES_ES = {
    "ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04",
    "MAYO": "05", "JUNIO": "06", "JULIO": "07", "AGOSTO": "08",
    "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12",
}


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
                "retiradas": RETIRADAS,
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
    cortes = set()
    for col_ano, col_per in (("ano", "periodo"),):
        if col_ano in df.columns:
            for a, p in zip(df[col_ano].astype(str), df[col_per].astype(str) if col_per in df.columns else [""] * len(df), strict=False):
                a = a.strip()
                if re.fullmatch(r"20\d{2}", a):
                    mes = MESES_ES.get(p.strip().upper(), "01")
                    cortes.add(f"{a}-{mes}")
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
        "corte": max(cortes) if cortes else "",
    }


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
    cortes = [k for subs in serie.values() for k in (r["trimestre"] for r in subs)]
    corte = max(cortes, key=lambda t: trim_key(t) or (0, 0)) if cortes else ""
    return {"conceptos": conceptos, "serie": serie, "corte": corte}


def main():
    global RAW_DIR
    try:
        from export.rawutil import latest_raw
        if Path(sys.argv[0]).name.startswith("bureau_oferta") and len(sys.argv) > 1 and Path(sys.argv[1]).is_dir():
            RAW_DIR = Path(sys.argv[1])
        else:
            found = latest_raw(ROOT)
            if found is not None:
                RAW_DIR = found
        faltantes = [f for f in REQUIRED_FILES if (RAW_DIR / f).is_file() is False]
        rnt_dfs = []
        for f in RNT_FILES:
            df = load_csv(f)
            if df is not None:
                rnt_dfs.append(df)
        if not rnt_dfs:
            faltantes = RNT_FILES + faltantes

        vacios = []
        for f in REQUIRED_FILES:
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

        turismo = load_csv("dane_egit_turismo_interno.csv")
        if turismo is None or turismo.empty:
            skip("RAW ilegible o sin filas en dane_egit_turismo_interno.csv")
            return 0

        rnt = build_rnt(rnt_dfs)
        t_interno = build_turismo_interno(turismo)
        serie = {"rnt": rnt, "turismo_interno": t_interno}
        cortes = {"rnt": rnt.get("corte", ""), "turismo_interno": t_interno.get("corte", "")}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(
            json.dumps(
                {
                    "id": ID,
                    "generado": hoy(),
                    "ventana": VENTANA,
                    "fuente": FUENTE,
                    "serie": serie,
                    "cortes": cortes,
                    "retiradas": RETIRADAS,
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
