# Feature: Rotar 7 SKIP por 7 vivas

Objetivo: borrar las 7 fuentes en SKIP persistente y reemplazarlas por 7 nuevas verificadas vivas hoy, todas free y temáticas. 30 extractores antes y después. Branch: feature/bureau-etl-funnel.
Estrategia delivery: parent borra y cablea (archivos compartidos), workers crean las 7 nuevas en background con superficies disjuntas.

## Specs
- S1: "las que estás con skip borralas y busca más fuentes" — verbatim usuario 28-oct.
- S2: Borrar: `oecd_tourism`, `youtube_rss`, `osm_oferta`, `eventos_cultura_med`, `wttc_eir`, `gated_amadeus`, `gated_brand24` (+ su cableado en daily.py/sources.yml). Se conservan `eurostat_aviation` y `rnt_prestadores` (rescatadas con datos).
- S3: Nuevas 7, endpoints verificados vivos por el parent el 28-oct: `wb_departures` (WB ST.INT.DPRT 200), `eurostat_capacity` (tour_cap_nat 200), `eurostat_demanda` (familia dissemination 200), `gdelt_docs` (DOC API existe, 429 con backoff), `rnt_antioquia` (Socrata mmsn-v5r4/u69p-k7vd), `aerocivil_flota` (Socrata djjf-g4q4+w9ei-uhm3), `aire_med` (Open-Meteo AQ 200).
- S4: Patrón `extract/base.py`, jamás tumba el daily, sin nuevas dependencias. Amadeus/Brand24 se van sin reemplazo directo (requieren credenciales del Bureau).

## Tasks
- [ ] T1 (S2) Parent: borrar 7 archivos + cableado daily.py/sources.yml — route: inline
- [ ] T2 (S3,S4) W1: wb_departures, eurostat_capacity, eurostat_demanda, gdelt_docs — route: delegated background worker
- [ ] T3 (S3,S4) W2: rnt_antioquia, aerocivil_flota, aire_med — route: delegated background worker
- [x] T4 (S1) Parent: cablear 7 nuevas + verificar 30/30 con datos — route: inline — done 28-oct (daily.main 30 extractores, import OK, COMPILE_OK; pyright limpio tras re-exports en extract/__init__.py)
- [x] T5 (S1) Borrar `gdelt_docs` (ban IP persistente) + reemplazo vivo verificado — route: inline — done 28-oct (`terminales_med` 336 filas aesn-q83n+a45t-7a3r, daily.main 30, daily.py limpio)

## Log
- L1 (2026-10-28): "las que estás con skip borralas y busca más fuentes"
- Decisión 28-oct: borrado real de archivos (no solo SKIP). Reemplazos elegidos de la misma familia de APIs ya probadas vivas.
- Next: T1 borrado, luego W1-W2, luego T4.
