# Feature: Fuentes tanda-1 public-apis

Objetivo: cablear 5 extractores nuevos sin-key desde public-apis/public-apis que alimenten dashboard Bureau (conectividad, emisores, costos, FX, clima-riesgo). Solo fuentes abiertas, gratis, sin login ni paywall. Patrón `extract/base.py` (`save_or_carry`, UA), `run()` individual + agregador, nunca tumba el daily, SKIP honesto con carry-forward. Sin nuevas dependencias (requests+pandas).

## Specs
- S1: "https://github.com/public-apis/public-apis ya extrajiste de acá todas las apis que tienen que ver con turismo? o qué pueden alimentar nuestro dashboard?" — verbatim usuario 02-nov.
- S2: "¿Querías decir que sí arme la tanda 1 sin-key para el dashboard?" → "Sí, implementá tanda 1" — verbatim decisión usuario 02-nov.
- S3: Patrón obligatorio `extract/base.py` (`save`/`save_or_carry`, `out_dir`, UA), `run()` individual + agregador, nunca levanta, SKIP honesto con carry-forward. Sin nuevas dependencias.
- S4 (airportmiles): AirportMiles expone códigos/distancias/rutas/pax como JSON (sitio Nuxt, payload `/_payload.json`). Extractor intenta payload + parse aeropuertos MDE/EOH; si cambia el build-id → vacío + carry. Columnas: `iata, nombre, ciudad, pais, lat, lon, fuente`.
- S5 (emisores-contexto, pivot canienter): Can I enter cobra API a empresas ("API de pago por solicitud") → NO se cablea por regla solo-gratis. En su lugar `emisores_contexto` desde Graph Countries raw (github, sin key): moneda, idiomas, región, fronteras por cca3 para top emisores. Columnas: `cca3, nombre, region, moneda, idiomas, fronteras`.
- S6 (tieredtravel): TieredTravel `GET https://tieredtravel.com/api/v1/destinations` (+ `/api/v1/hotels`, `/api/v1/attractions`) sin key, auth opcional. Filtrar slug medellin/Medellín; guardar costos tiers + conteos. Columnas: `slug, nombre, pais, costo_budget, costo_mid, costo_luxury, n_hoteles, n_atracciones`.
- S7 (fx-cop, pivot frankfurter): Frankfurter verificado hoy devuelve solo EUR (`{"rates":{"EUR":0.89}}`, sin COP) → no sirve para derrama COP. En su lugar `fx_cop` desde `https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json` (sin key, `date` + `usd.cop/eur/mxn/brl`, verificado COP=3201 el 2026-11-01). Columnas: `base, date, cop, eur, mxn, brl`.
- S8 (clima-ensemble): Open-Meteo Ensemble `https://ensemble-api.open-meteo.com/v1/ensemble?latitude=6.25&longitude=-75.57&daily=temperature_2m_max,precipitation_sum&timezone=America%2FBogota&models=icon_seamless` (verificado 200 con `models=icon_seamless`; sin `models` da 400 `best_match not supported`). Guardar spread diario P10-P90 lluvia para riesgo outdoor MICE. Columnas: `date, tmax_mean, prec_mean, prec_p10, prec_p90, n_members`.

## Tasks
- [x] T1 (S3,S4) airportmiles — done (4 tests)
- [x] T2 (S3,S5) emisores_contexto — done (3 tests)
- [x] T3 (S3,S6) tieredtravel_med — done (5 tests)
- [x] T4 (S3,S7) fx_cop — done (3 tests)
- [x] T5 (S3,S8) openmeteo_ensemble — done (3 tests)
- [x] T6 (S1-S8) Parent wire daily.py + sources.yml + verificación 5/5 — done (18/18, DAILY_IMPORT_OK)

## Log
- L1 (2026-11-02): usuario pregunta si ya se extrajo de public-apis/public-apis lo de turismo y qué puede alimentar el dashboard.
- L2 (2026-11-02): usuario autoriza "Sí, implementá tanda 1".
- L3 (2026-11-02): probes parent: frankfurter sin COP (solo EUR) → pivot a currency-api con COP; ensemble exige `models=icon_seamless`; canienter API paga → pivot a graph-countries gratis; tieredtravel openapi `/api/v1/destinations|hotels|attractions` sin key; airportmiles vía `/_payload.json` Nuxt.
- Next: lanzar T1-T5 en background, luego T6 parent.
- L4 (2026-11-02): commiteado en 2 slices sobre feature/bureau-etl-funnel: 957a0ab (T1,T2,T4, 490 ins) + 009ca1f (T3,T5,T6 wire, 435 ins). 18/18 tests, DAILY_IMPORT_OK.
