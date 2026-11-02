# Propuesta de conversoras para `alimentar_bureau.py` (repo tableros-bureau)

Pegar estas 4 funciones en `scripts/alimentar_bureau.py`, llamarlas en `__main__`
y agregar las 4 tuplas al `manifiesto()`. Nuestros JSON ya están publicados en
`etl-bureau/export/tableros_bureau/` (misma BASE raw que las piezas actuales).

```python
def oferta():
    try:
        src = bajar("oferta_territorio_2025_2026.json")
    except Exception as exc:
        ERRORES.append("oferta: " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
        print("falla oferta, se conserva el anterior")
        return
    s = src.get("serie", {})
    guardar("bureau_oferta.json", {
        "id": "bureau-oferta",
        "titulo": "Oferta y territorio (ETL Bureau)",
        "fuente": "ETL Bureau, RNT + MEData + DANE EGIT " + str(src.get("ventana", "")),
        "ventana": str(src.get("ventana", "")),
        "url": BASE + "/oferta_territorio_2025_2026.json",
        "licencia": "Agregados propios del ETL; fuentes primarias datos.gov.co / DANE / MEData.",
        "universo": "Prestadores RNT, tarifa y ocupación por zona, uplift de 6 temporadas, turismo interno.",
        "serie": s.get("temporadas", []) + s.get("tarifa_zona", []) + s.get("ocupacion_zonas", []),
        "rnt": s.get("rnt", {}),
        "turismo_interno": s.get("turismo_interno", {}),
    })
    print("oferta ok")


def seguridad():
    try:
        src = bajar("seguridad_2025_2026.json")
    except Exception as exc:
        ERRORES.append("seguridad: " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
        print("falla seguridad, se conserva el anterior")
        return
    guardar("bureau_seguridad.json", {
        "id": "bureau-seguridad",
        "titulo": "Seguridad ciudadana Medellín (ETL Bureau)",
        "fuente": "ETL Bureau, SIEDCO Policía Nacional " + str(src.get("ventana", "")),
        "ventana": str(src.get("ventana", "")),
        "url": BASE + "/seguridad_2025_2026.json",
        "licencia": "Datos abiertos SIEDCO; agregados propios del ETL.",
        "universo": "Homicidios y hurtos ciudad; hurtos sin desagregación por zona (null, no 0).",
        "serie": src.get("serie_mensual", []),
        "top_zonas": src.get("top_zonas", []),
        "top_modalidades": src.get("top_modalidades", []),
    })
    print("seguridad ok")


def clima():
    try:
        src = bajar("clima_aire_2025_2026.json")
    except Exception as exc:
        ERRORES.append("clima: " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
        print("falla clima, se conserva el anterior")
        return
    guardar("bureau_clima.json", {
        "id": "bureau-clima",
        "titulo": "Clima y calidad del aire (ETL Bureau)",
        "fuente": "ETL Bureau, IDEAM + Open-Meteo + aire_med " + str(src.get("ventana", "")),
        "ventana": str(src.get("ventana", "")),
        "url": BASE + "/clima_aire_2025_2026.json",
        "licencia": "Datos abiertos IDEAM/Open-Meteo; agregados propios del ETL.",
        "universo": "Lluvia mensual agregada, PM2.5 diario, pronóstico ensemble 7 días.",
        "serie": src.get("lluvia_mensual", []),
        "pm25_serie": src.get("pm25_serie", []),
        "pronostico": src.get("pronostico", []),
    })
    print("clima ok")


def conectividad_bench():
    try:
        src = bajar("conectividad_benchmark_2025_2026.json")
    except Exception as exc:
        ERRORES.append("conectividad_bench: " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
        print("falla conectividad_bench, se conserva el anterior")
        return
    guardar("bureau_conectividad.json", {
        "id": "bureau-conectividad",
        "titulo": "Conectividad ampliada y benchmarks (ETL Bureau)",
        "fuente": "ETL Bureau, Aerocivil/terminales/DANE/Eurostat/WB/Wikimedia " + str(src.get("ventana", "")),
        "ventana": str(src.get("ventana", "")),
        "url": BASE + "/conectividad_benchmark_2025_2026.json",
        "licencia": "Agregados propios del ETL; fuentes primarias datos.gov.co / Eurostat / Banco Mundial.",
        "universo": "Oferta aérea (sillas/vuelos), operaciones, terrestre, metro, TRM, costos, benchmarks EU/mundo, digital.",
        "serie": src.get("operaciones_serie", []) + src.get("terrestre_serie", []),
        "oferta_aerea": src.get("oferta_aerea", {}),
        "metro_serie": src.get("metro_serie", []),
        "trm_serie": src.get("trm_serie", []),
        "costos_destino": src.get("costos_destino", []),
        "benchmark_eu": src.get("benchmark_eu", []),
        "benchmark_mundo": src.get("benchmark_mundo", []),
        "wikimedia_serie": src.get("wikimedia_serie", []),
        "travel_metrics": src.get("travel_metrics", []),
        "skips": src.get("skips", []),
    })
    print("conectividad_bench ok")
```

Manifiesto: agregar a la lista de tuplas
`("bureau_oferta.json", "bureau-oferta", "serie")`,
`("bureau_seguridad.json", "bureau-seguridad", "serie")`,
`("bureau_clima.json", "bureau-clima", "serie")`,
`("bureau_conectividad.json", "bureau-conectividad", "serie")`
y las 4 llamadas en `__main__`.

Notas:
- `benchmark_eu` trae 6471 filas (JSON nuestro: 777 KB). Si prefieren agregados,
  avisar y se recorta del lado ETL.
- `top_zonas[].hurtos` es `null` (el raw de hurtos no trae zona): tratar como
  "no disponible", no como 0.
- `serie_mensual` de seguridad arranca en 2018-07: filtrar por `periodo` si el
  tablero quiere solo 2025–2026.
