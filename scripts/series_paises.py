# -*- coding: utf-8 -*-
"""Completa país-mes, residencia, ocupación y Wikipedia. Si una fuente falla, el JSON anterior queda."""
import json
import traceback
from pathlib import Path

import preparar_fuentes as p

OUT = Path(__file__).resolve().parents[1] / "data" / "open"
ERRORES = []


def fallo(nombre, exc):
    texto = nombre + ": " + "".join(traceback.format_exception_only(type(exc), exc)).strip()
    ERRORES.append(texto)
    print("fallo", texto)


def manifiesto():
    piezas = []
    errores = list(ERRORES)
    for nombre, clave in (
        ("conectividad.json", "serie"),
        ("wikipedia.json", "serie"),
        ("gdelt.json", "serie"),
        ("ema.json", "serie"),
        ("medata_tarifas.json", "serie"),
        ("icca.json", "ciudades"),
        ("evi.json", "olas"),
        ("huella.json", "serie"),
    ):
        path = OUT / nombre
        if not path.exists():
            if nombre == "gdelt.json":
                continue
            errores.append(nombre + ": no está en disco")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        piezas.append({
            "archivo": "data/open/" + nombre,
            "id": payload.get("id"),
            "estado": payload.get("estado", "ok"),
            "n": len(payload.get(clave) or []),
        })
    doc = {
        "generado": p.HOY,
        "piezas": piezas,
        "errores": errores,
        "mercados": p.MERCADOS,
        "destinos_comparables": p.DESTINOS,
        "nota": "Agregados para el tablero. Sin filas de encuesta y sin XLSX crudos. Las simulaciones del navegador no entran aquí.",
    }
    p.write("manifiesto.json", doc)
    print("manifiesto", [(x["id"], x["n"]) for x in piezas])


def paises():
    serie = p.paises_mensuales()
    con = json.loads((OUT / "conectividad.json").read_text(encoding="utf-8"))
    con["paises"] = serie
    con["nota_paises"] = "Serie mensual de cada país de origen o destino. La serie por mercado priorizado no cambia."
    p.write("conectividad.json", con)
    print("paises", len(serie))


def wiki():
    payload = p.wikipedia()
    if not any(row.get("destino") == "Medellín" for row in payload.get("serie") or []):
        raise RuntimeError("Wikipedia no trajo Medellín. Se conserva el JSON anterior.")
    p.write("wikipedia.json", payload)
    print("wikipedia", len(payload["serie"]), "articulos", len(payload.get("articulos") or []))


def ocupacion():
    payload = p.ema()
    serie = (payload.get("ocupacion") or {}).get("serie") or []
    if not serie or "regiones" not in serie[-1]:
        raise RuntimeError("La ocupación no trajo las regiones. Se conserva el JSON anterior.")
    p.write("ema.json", payload)
    print("ocupacion", len(serie), "regiones", len(serie[-1]["regiones"]))


def evi():
    payload = p.agregar_evi()
    for ola in payload.get("olas") or []:
        ola.pop("paises_peso", None)
    if not payload.get("olas"):
        raise RuntimeError("La EVI no trajo olas. Se conserva el JSON anterior.")
    p.write("evi.json", payload)
    print("evi", [(ola["ola"], len(ola.get("residencia") or [])) for ola in payload["olas"]])


def gdelt():
    payload = p.gdelt()
    if not payload.get("serie"):
        raise RuntimeError("GDELT respondió sin puntos. El hueco queda vacío.")
    p.write("gdelt.json", payload)
    print("gdelt", len(payload["serie"]))


if __name__ == "__main__":
    for nombre, fn in (("paises", paises), ("wikipedia", wiki), ("ema", ocupacion), ("evi", evi), ("gdelt", gdelt)):
        try:
            print("corre", nombre)
            fn()
        except Exception as exc:
            fallo(nombre, exc)
            print(traceback.format_exc(limit=3))
    manifiesto()
