"""API lectura del backend post-embudo LLM.

Uso local:  uvicorn api.main:app --port 8080
Env: BACKEND_DATABASE_URL (o DATABASE_URL). Sin URL -> 503 honesto.
"""
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import db

app = FastAPI(title="bureau-llm-backend")


def _con():
    if not db.get_url():
        raise HTTPException(503, "sin BACKEND_DATABASE_URL")
    try:
        return db.connect()
    except Exception as e:
        raise HTTPException(503, f"sin conexion ({e})")


@app.get("/health")
def health():
    if not db.get_url():
        return {"db": "sin_url"}
    try:
        con = db.connect()
        con.execute("SELECT 1")
        con.close()
        return {"db": "ok"}
    except Exception as e:
        return {"db": f"error: {e}"}


@app.get("/marca")
def marca(dia: str = Query("", description="YYYY-MM-DD; vacio = ultimo dia")):
    con = _con()
    try:
        with con.cursor() as cur:
            if not dia:
                row = cur.execute("SELECT MAX(dia)::text FROM marca_llm").fetchone()
                dia = row[0] if row and row[0] else ""
            if not dia:
                return {"dia": "", "rows": []}
            cur.execute(
                "SELECT categoria, n, share, sent_net, top_topico FROM marca_llm"
                " WHERE dia = %s ORDER BY n DESC", (dia,))
            cols = [d[0] for d in cur.description]
            return {"dia": dia, "rows": [dict(zip(cols, r)) for r in cur.fetchall()]}
    finally:
        con.close()


@app.get("/clasificacion")
def clasificacion(dia: str = Query(""), categoria: str = Query(""), limit: int = Query(200, le=2000)):
    con = _con()
    try:
        with con.cursor() as cur:
            if not dia:
                row = cur.execute("SELECT MAX(dia)::text FROM clasificacion_llm").fetchone()
                dia = row[0] if row and row[0] else ""
            if not dia:
                return {"dia": "", "rows": []}
            q = ("SELECT fecha, medio, titulo, link, categoria, sentimiento, topico, modelo"
                 " FROM clasificacion_llm WHERE dia = %s")
            params: list = [dia]
            if categoria:
                q += " AND categoria = %s"
                params.append(categoria)
            q += " ORDER BY titulo LIMIT %s"
            params.append(limit)
            cur.execute(q, params)
            cols = [d[0] for d in cur.description]
            return {"dia": dia, "rows": [dict(zip(cols, r)) for r in cur.fetchall()]}
    finally:
        con.close()


@app.get("/informes")
def informes(corte: str = Query("", description="vacio = ultimo corte")):
    con = _con()
    try:
        with con.cursor() as cur:
            if not corte:
                row = cur.execute("SELECT MAX(corte) FROM informes").fetchone()
                corte = row[0] if row and row[0] else ""
            if not corte:
                return {"corte": "", "rows": []}
            cur.execute(
                "SELECT seccion, titulo, bullets, cifras FROM informes"
                " WHERE corte = %s ORDER BY seccion", (corte,))
            cols = [d[0] for d in cur.description]
            return {"corte": corte, "rows": [dict(zip(cols, r)) for r in cur.fetchall()]}
    finally:
        con.close()
