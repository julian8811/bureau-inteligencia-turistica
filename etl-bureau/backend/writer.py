"""Writer post-embudo LLM -> Postgres. Nunca tumba el daily: sin URL o sin
conexion retorna skip; los CSV que falten cuentan 0."""
import os
from datetime import date
from pathlib import Path

import pandas as pd

from . import db

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
RAW = BASE / "data" / "raw"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"

SKIP = {"status": "skip", "dia": "", "marca": 0, "clasificacion": 0}


def _latest_clasificacion():
    cands = sorted(RAW.glob("*/clasificacion_llm.csv"))
    return cands[-1] if cands else None


def run() -> dict:
    if not db.get_url():
        print("[backend][SKIP] sin BACKEND_DATABASE_URL")
        return dict(SKIP)
    try:
        con = db.connect()
    except Exception as e:
        print(f"[backend][SKIP] sin conexion ({e})")
        return dict(SKIP)
    try:
        with con:
            with con.cursor() as cur:
                for stmt in SCHEMA.read_text().split(";"):
                    if stmt.strip():
                        cur.execute(stmt)
            dia = _latest_clasificacion()
            dia_str = dia.parent.name if dia else date.today().isoformat()
            n_clas = _write_clasificacion(con, dia, dia_str)
            n_marca = _write_marca(con, dia_str)
        print(f"[backend] ok dia={dia_str} marca={n_marca} clasificacion={n_clas}")
        return {"status": "ok", "dia": dia_str, "marca": n_marca, "clasificacion": n_clas}
    except Exception as e:
        print(f"[backend][SKIP] error escribiendo ({e})")
        return dict(SKIP)
    finally:
        try:
            con.close()
        except Exception:
            pass


def _write_clasificacion(con, path, dia_str: str) -> int:
    if not path:
        return 0
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[backend][WARN] clasificacion: no se pudo leer ({e})")
        return 0
    if df.empty:
        return 0
    cols = ["fecha", "medio", "titulo", "link", "categoria", "sentimiento", "topico", "modelo"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols].fillna("")
    rows = [(dia_str,) + tuple(r) for r in df.itertuples(index=False, name=None)]
    # dedup por PK dentro del lote (el CSV puede traer el mismo titular dos veces)
    seen, uniq = set(), []
    for r in rows:
        key = (r[0], r[3], r[2])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    with con.cursor() as cur:
        cur.execute("DELETE FROM clasificacion_llm WHERE dia = %s", (dia_str,))
        cur.executemany(
            "INSERT INTO clasificacion_llm (dia, fecha, medio, titulo, link, categoria, sentimiento, topico, modelo)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [(u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8]) for u in uniq],
        )
    return len(uniq)


def _write_marca(con, dia_str: str) -> int:
    path = PROC / "marca_llm.csv"
    if not path.exists():
        return 0
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[backend][WARN] marca: no se pudo leer ({e})")
        return 0
    if df.empty:
        return 0
    rows = []
    for _, r in df.iterrows():
        rows.append((dia_str, str(r.get("categoria", "")), int(r.get("n", 0) or 0),
                     float(r.get("share", 0) or 0), float(r.get("sent_net", 0) or 0),
                     str(r.get("top_topico", ""))))
    with con.cursor() as cur:
        cur.execute("DELETE FROM marca_llm WHERE dia = %s", (dia_str,))
        cur.executemany(
            "INSERT INTO marca_llm (dia, categoria, n, share, sent_net, top_topico)"
            " VALUES (%s, %s, %s, %s, %s, %s)", rows)
    return len(rows)


if __name__ == "__main__":
    print(run())
