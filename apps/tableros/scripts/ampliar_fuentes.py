# -*- coding: utf-8 -*-
"""Agrega cortes nuevos sin repetir Wikipedia, ICCA ni la huella ya calculada."""
import json
import traceback
from pathlib import Path

import preparar_fuentes as p

OUT = Path(__file__).resolve().parents[1] / "data" / "open"


def guardar_manifiesto(error_gdelt):
    piezas = []
    errores = []
    if error_gdelt:
        errores.append("gdelt.json: " + error_gdelt)
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
        "nota": "Agregados para el tablero. Sin filas de encuesta y sin XLSX crudos.",
    }
    (OUT / "manifiesto.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("manifiesto", [(x["id"], x["n"]) for x in piezas])


if __name__ == "__main__":
    cortes = p.cortes_aerocivil()
    con = json.loads((OUT / "conectividad.json").read_text(encoding="utf-8"))
    con.update(cortes)
    p.write("conectividad.json", con)
    print("aero", len(cortes["aeropuertos"]), len(cortes["aerolineas"]), len(cortes["carga"]))

    evi = p.agregar_evi()
    for ola in evi.get("olas") or []:
        ola.pop("paises_peso", None)
    p.write("evi.json", evi)
    print("evi olas", len(evi.get("olas") or []), "meses", len(evi.get("meses") or []))

    ema = p.ema()
    p.write("ema.json", ema)
    print("ocupacion", len((ema.get("ocupacion") or {}).get("serie") or []))

    error = None
    try:
        gd = p.gdelt()
        p.write("gdelt.json", gd)
        print("gdelt", len(gd["serie"]))
    except Exception:
        error = traceback.format_exc(limit=2)
        print("gdelt fallo")
        print(error)
    guardar_manifiesto(error)
