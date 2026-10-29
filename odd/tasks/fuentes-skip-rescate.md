# Feature: Rescate fuentes SKIP (9)

Objetivo: conectar y extraer datos de las 9 fuentes que hoy están en SKIP honesto, sin key paga ni login. Branch: feature/bureau-etl-funnel.
Estrategia delivery: slices por fuente, workers background con superficies disjuntas; parent verifica.

## Specs
- S1: "trata ka forma de conectar y extraer datos de las que están skip" — verbatim usuario 28-oct.
- S2: Las 9 en SKIP: `oecd_tourism` (NonProduction), `wttc_eir` (muro), `gated_amadeus` (sin key), `gated_brand24` (sin CSV/key), `eurostat_aviation` (avia_par 404), `osm_oferta` (Overpass bloqueado), `youtube_rss` (channel IDs marcadores), `eventos_cultura_med` (sin dataset), `rnt_prestadores` (sin dataset).
- S3: Patrón `extract/base.py` (save/save_or_carry, timeouts, jamás tumba el daily). Si una fuente exige key paga o login, se documenta y queda en SKIP honesto con instrucciones, no se simulan datos.
- S4: Cada rescate trae evidencia: filas extraídas hoy o motivo verificado del SKIP persistente.

## Tasks
- [x] T1 (S2,S3) Rescatar Eurostat avia (avia_paoc 200) + OECD (dataflow alternativo) — route: delegated background worker — done 28-oct (avia 7776 filas; oecd SKIP 0 series verificado)
- [x] T2 (S2,S3) Rescatar YouTube IDs oficiales + OSM mirrors + eventos/RNT vía catálogo Socrata — route: delegated background worker — done 28-oct (rnt 559 Medellín; youtube/osm/eventos SKIP honesto verificado)
- [x] T3 (S2,S3) Rescatar Amadeus/Brand24/WTTC free (test API, trial CSV, factsheets) o documentar muro — route: delegated background worker — done 28-oct (amadeus/brand24 SKIP sin creds; wttc SKIP muro verificado)
- [x] T4 (S1,S4) Parent: verificar 9 + actualizar feature doc — route: inline — done 28-oct (ALL_COMPILE_OK, 2 rescatadas + 7 SKIP honesto)

## Log
- L1 (2026-10-28): "trata ka forma de conectar y extraer datos de las que están skip"
- Next: diagnosticar endpoints y lanzar T1-T3.
