# Feature: Trazabilidad KPI ↔ fuentes

Objetivo: revisar los ~50 KPIs calculados y verificar que cada uno tenga fuente viva que lo alimente, con matriz de trazabilidad y cierre de brechas. Branch: feature/bureau-etl-funnel.

## Specs
- S1: "necesitamos revisar bien los kpis y que la información que arrastramos si respondan a esos kpis" — verbatim usuario 28-oct.
- S2: Cada KPI del `kpis_historico.csv` + derivados (pais, destinos, ult3m, desglose, marca_llm) debe mapear a ≥1 CSV raw con datos vivos hoy; si no, se marca brecha (fuente caída, extractor en SKIP o KPI huérfano).
- S3: Seguridad: la GROQ key expuesta en chat el 28-oct NO se usa ni se guarda; el dueño la revoca y exporta una nueva localmente.
- S4: Sin frontend; el entregable es la matriz + brechas cerradas en transform/load.

## Tasks
- [ ] T1 (S2) Matriz KPI→fuente con estado vivo/caído por cada KPI — route: inline
- [x] T2 (S1,S2) Cerrar brechas: reconectar, carry o documentar SKIP honesto — route: delegated worker — done 28-oct (kpis_nuevas() con 20 claves, try/except por fuente, merge en run())
- [x] T3 (S4) Verificación: daily OK + matriz final sin huérfanos injustificados — route: inline — done 28-oct (COMPILE_OK, 0 missing, historico 46→66 cols, daily import OK)

## Matriz KPI→fuente (corte 2026-10-28)

transform/kpis.py consume 16 raws (`latest_raw`). Estado hoy:
- Vivos con datos (14): alerts_rss 473, medellin_no_residentes 16037, aereo_mde_eoh 62011, dane_egit_gasto_dia 513, entradas_nacionalidad 181186, salidas_destino 93017, google_trends 465, ciudades_llegadas 10946, medata_ocupacion_med 202, medata_tarifa_med 134, medata_pits 1578, medata_sitios 1457, medata_extranjeros_pais 8743, medata_occ_feria 244 (+crm.xlsx 5 filas para MICE).
- Caídos/ausentes honestos (2): dane_enh (DANE bloquea bots, no existe el CSV; kpi dane_enh_ok=0), gdelt_marca (0 filas hoy por 429; gdelt_vol_7d=0).
- 46 columnas en kpis_historico.csv.

Arrastrado con datos pero SIN KPI que lo agregue (~20 fuentes): eurostat_tourism/aviation/capacity/demanda/arrivals, wb_arrivals/receipts/departures, rnt_prestadores/antioquia, seguridad_hurtos/homicidios, metro/movilidad_terminales, ideam x3, conectividad x2, alumbrados, prensa, wikimedia, openmeteo, trm, festivos, aire_med, terminales_med, aerocivil_flota, medata_mig/pax/zona/travel. Van a load/web pero ningún KPI los resume: esa es la brecha.
- clasificacion_llm: pendiente de key nueva (la expuesta se revoca, no se usa).

## Log
- L1 (2026-10-28): "necesitamos revisar bien los kpis y que la información que arrastramos si respondan a esos kpis"
- L2 (2026-10-28): usuario pegó GROQ_API_KEY en el chat; instruido revocar y rotar, no se almacena ni se usa.
- Next: T1 matriz.
