"""Snapshot JSON del backend para tableros-bureau (Vercel estatico).

Uso: python3 -m backend.export_snapshot [dir_salida]
Sin BACKEND_DATABASE_URL -> skip honesto (no escribe nada).
"""
import json
import sys
from pathlib import Path

from . import db

BASE = Path(__file__).resolve().parents[1]
DEFAULT_OUT = BASE / "export" / "backend_snapshot"


def run(out_dir: str = "") -> dict:
    if not db.get_url():
        print("[snapshot][SKIP] sin BACKEND_DATABASE_URL")
        return {"status": "skip", "files": []}
    try:
        con = db.connect()
    except Exception as e:
        print(f"[snapshot][SKIP] sin conexion ({e})")
        return {"status": "skip", "files": []}
    try:
        out = Path(out_dir) if out_dir else DEFAULT_OUT
        out.mkdir(parents=True, exist_ok=True)
        with con.cursor() as cur:
            row = cur.execute("SELECT MAX(dia)::text FROM marca_llm").fetchone()
            dia = row[0] if row and row[0] else ""
            cur.execute("SELECT categoria, n, share, sent_net, top_topico FROM marca_llm"
                        " WHERE dia = %s ORDER BY n DESC", (dia,))
            cols = [d[0] for d in cur.description]
            marca = {"dia": dia or "", "rows": [dict(zip(cols, r)) for r in cur.fetchall()]}
            row = cur.execute("SELECT MAX(corte) FROM informes").fetchone()
            corte = row[0] if row and row[0] else ""
            rows = []
            if corte:
                cur.execute("SELECT seccion, titulo, bullets, cifras FROM informes"
                            " WHERE corte = %s ORDER BY seccion", (corte,))
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            informes = {"corte": corte or "", "rows": rows}
        (out / "marca_llm.json").write_text(json.dumps(marca, ensure_ascii=False, indent=1))
        (out / "informes.json").write_text(json.dumps(informes, ensure_ascii=False, indent=1))
        return {"status": "ok", "files": ["informes.json", "marca_llm.json"]}
    finally:
        con.close()


if __name__ == "__main__":
    print(run(sys.argv[1] if len(sys.argv) > 1 else ""))
