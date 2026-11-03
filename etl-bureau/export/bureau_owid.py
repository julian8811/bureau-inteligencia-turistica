"""Benchmark mundial OWID (UN Tourism) -> tableros-bureau.

Descarga el CSV de Our World in Data (llegadas de turistas internacionales,
1995-2024, sin llave) y publica
export/tableros_bureau/owid_benchmark_2025_2026.json.
Si la descarga falla, conserva el JSON anterior (exit 0, estado del previo).
Agrega: top 25 del último año, serie completa de Colombia y totales por región.
"""
import contextlib
import datetime
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent  # export/
OUT = BASE / "tableros_bureau" / "owid_benchmark_2025_2026.json"
URL = "https://ourworldindata.org/grapher/international-tourist-trips.csv"
UA = {"User-Agent": "BureauETL/1.0"}
FUENTE = "ETL Bureau, Our World in Data (UN Tourism, llegadas internacionales)"


def hoy():
    return datetime.date.today().isoformat()


def main() -> int:
    try:
        partes = urllib.parse.urlparse(URL)
        if partes.scheme != "https" or partes.hostname != "ourworldindata.org":
            raise ValueError("URL fuera del dominio permitido")
        with urllib.request.urlopen(
            "https://ourworldindata.org/grapher/international-tourist-trips.csv",
            timeout=60,
        ) as resp:
            texto = resp.read().decode("utf-8")
    except Exception as ex:
        with contextlib.suppress(Exception):
            print(f"OK {OUT} estado=previo motivo=descarga: {type(ex).__name__}")
        return 0
    try:
        lineas = [ln for ln in texto.splitlines() if ln.strip()]
        cab = [c.strip() for c in lineas[0].split(",")]
        i_ent = cab.index("Entity")
        i_cod = cab.index("Code")
        i_anio = cab.index("Year")
        i_val = [i for i, c in enumerate(cab) if "rrival" in c][0]
        i_reg = cab.index("World region according to OWID") if "World region according to OWID" in cab else -1
        filas = []
        for ln in lineas[1:]:
            p = ln.split(",")
            if len(p) <= max(i_ent, i_cod, i_anio, i_val):
                continue
            try:
                anio = int(p[i_anio].strip())
                valor = float(p[i_val].strip())
            except ValueError:
                continue
            if not valor or valor != valor:
                continue
            filas.append({
                "pais": p[i_ent].strip(),
                "iso3": p[i_cod].strip(),
                "anio": anio,
                "valor": int(valor),
                "region": p[i_reg].strip() if i_reg >= 0 and len(p) > i_reg else "",
            })
        if not filas:
            raise ValueError("sin filas validas")
        ultimo = max(r["anio"] for r in filas)
        top = sorted([r for r in filas if r["anio"] == ultimo],
                     key=lambda r: r["valor"], reverse=True)[:25]
        col = sorted([r for r in filas if r["iso3"] == "COL"],
                     key=lambda r: r["anio"])
        regs: dict[str, int] = {}
        for r in filas:
            if r["anio"] == ultimo and r["region"]:
                regs[r["region"]] = regs.get(r["region"], 0) + r["valor"]
        payload = {
            "id": "bureau-owid",
            "generado": hoy(),
            "ventana": f"1995-{ultimo}",
            "fuente": FUENTE,
            "serie": top,
            "colombia_serie": [{"anio": r["anio"], "valor": r["valor"]} for r in col],
            "regiones_ultimo": [{"region": k, "valor": v} for k, v in
                                sorted(regs.items(), key=lambda kv: kv[1], reverse=True)],
            "cortes": {"mundial": ultimo, "colombia": col[-1]["anio"] if col else 0},
            "estado": "ok",
        }
    except Exception as ex:  # nunca tumbar: degradar a skip honesto
        payload = {"id": "bureau-owid", "generado": hoy(), "ventana": "",
                   "fuente": FUENTE, "estado": "skip",
                   "motivo": f"parseo: {type(ex).__name__}: {ex}"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {OUT} estado={payload['estado']} "
          f"top={len(payload.get('serie', []))} col={len(payload.get('colombia_serie', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
