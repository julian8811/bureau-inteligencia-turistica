# Feature: Fuentes oficiales gratis automatizadas

Objetivo: subir de 7 a 11 fuentes automatizadas sumando la tanda oficiales gratis sin key ni pago. Branch: feature/bureau-etl-funnel. Runner: `python etl-bureau/orchestration/daily.py`.
Estrategia delivery: single-pr (forecast <400 líneas por slice).

## Specs
- S1: "Requerimos entonces, aumentar el número de fuentes automatizables." — verbatim usuario 28-oct.
- S2: Tanda elegida "Oficiales gratis" ("UN, Eurostat, WTTC, OECD sin key, diario") — respuesta usuario.
- S3: Cada extractor guarda `data/raw/<hoy>/<fuente>.csv` con patrón base (`save`/`save_or_carry`), nunca tumba el daily, SKIP honesto con carry-forward si la API falla.
- S4: Evidencia 28-oct: World Bank `ST.INT.ARVL` responde 200 (proxy UN viable); Eurostat `tour_occ_ninat` dio 500 con dims provisorias (hay que fijar dims correctas); OECD SDMX dio 500 (hay que fijar query); WTTC EIR full es gated, solo headline free.

## Tasks
- [x] T1 (S2,S3) `extract/eurostat_tourism.py` — noches `tour_occ_ninat` vía dissemination API — route: delegated worker — done 28-oct (450 filas, ex-500 resuelto)
- [x] T2 (S2,S3) `extract/un_wb_arrivals.py` — llegadas World Bank `ST.INT.ARVL` como proxy UN — route: delegated worker — done 28-oct (30 filas, 2021-2024 null en el API)
- [x] T3 (S2,S3) `extract/oecd_tourism.py` — inbound/key indicators vía SDMX con SKIP honesto — route: delegated worker — done 28-oct (SKIP: NonProductionDataflow, query cableada)
- [x] T4 (S2,S3) `extract/wttc_eir.py` — headline EIR free con SKIP honesto (full gated) — route: delegated worker — done 28-oct (SKIP: EIR full tras muro)
- [x] T5 (S1,S3) Wire `daily.py` + `sources.yml` + verificación (import, build, 4 CSV) — route: delegated worker — done 28-oct (daily import OK, COMPILE_OK)

## Log
- L1 (2026-10-28): "Requerimos entonces, aumentar el número de fuentes automatizables."
- Decisión 28-oct: tanda oficiales gratis primero; gated con key y manuales quedan para después. UN directo no tiene API free → proxy World Bank documentado como tal.
- Next: worker T1-T5.
