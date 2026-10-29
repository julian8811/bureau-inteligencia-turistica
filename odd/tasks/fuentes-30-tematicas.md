# Feature: Escalar a 30 fuentes temáticas

Objetivo: pasar de 13 extractores en `daily.py` a 30, todos con relación directa a turismo MICE / vacacional / marca Medellín. Solo fuentes abiertas, gratis, sin login ni paywall. Branch: feature/bureau-etl-funnel.
Estrategia delivery: single-pr por slices (máx ~400 líneas por commit), workers en background con superficies disjuntas; el parent cablea `daily.py` + `sources.yml` al final para no chocar.

## Specs
- S1: "requiero llegar a 30 fuentes, pero que tengan relación con la tematica que estamos realizando" — verbatim usuario 28-oct.
- S2: Conteo por extractor en `daily.py`: hoy 13 (google_trends, socrata_co, medata, dane_egit, gdelt_marca, un_wb_arrivals, eurostat_tourism, oecd_tourism, wttc_eir, alerts_rss, gated_amadeus, gated_brand24, gated_icca). Faltan 17.
- S3: Patrón obligatorio `extract/base.py` (`save`/`save_or_carry`, `out_dir`, UA), `run()` individual + agregador, nunca tumba el daily, SKIP honesto con carry-forward. Sin nuevas dependencias.
- S4: Trazabilidad temática por extractor: MICE = venues/eventos/clima/seguridad/TRM; vacacional = llegadas/gasto/noches/aviación/RNT/clima/festivos; marca = noticias/youtube/wiki/búsquedas.

## Tasks
- [x] T1 (S2,S3) W1: wb_receipts, eurostat_aviation, eurostat_arrivals, openmeteo_med, trm_co, festivos_co — route: delegated background worker 1 — done 28-oct (W1 completed, COMPILE_OK, CSVs verificados)
- [x] T2 (S2,S3) W2: wikimedia_views, osm_oferta, youtube_rss, prensa_rss, eventos_cultura_med, rnt_prestadores — route: delegated background worker 2 — done 28-oct (W2 completed, wiki 90 + prensa 58 vivos)
- [x] T3 (S2,S3) W3: seguridad_med, metro_movilidad, ideam_clima, conectividad_aerea, gastronomia_nocturna — route: delegated background worker 3 — done 28-oct (W3 completed, seguridad/ideam/metro/conectividad con datos)
- [x] T4 (S1,S3,S4) Parent: wire daily.py + sources.yml (17 pasos) + verificación 30/30 — route: inline — done 28-oct (30 extractores en daily, 17 imports OK, COMPILE_OK)

## Log
- L1 (2026-10-28): "requiero llegar a 30 fuentes, pero que tengan relación con la tematica que estamos realizando"
- Decisión 28-oct: 13 extractores hoy → +17 nuevos = 30. Gated de pago (GlobalData, Amadeus feed, STR, ICCA full) quedan fuera por requerir contrato; se cubren con proxies free (WB, Eurostat, OSM, RNT, Overpass).
- Next: lanzar W1-W3 en background, luego T4 parent.
