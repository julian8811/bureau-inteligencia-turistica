# Feature: Embudo automatizado Bureau Medellín — ETL diario + Power BI

Objetivo: scrapear/extraer a diario solo fuentes permitidas (APIs oficiales, CSV, RSS, HTML público) y alimentar 3 tableros (Reuniones / Vacacional / Marca). Branch: feature/bureau-etl-funnel. Runner: Python 3.11 + cron/systemd + Power BI DirectQuery/Scheduled Refresh.
Estrategia delivery: single-pr (forecast <400 líneas por slice).

## Specs
- S1: "armemos un embudo automatizado que screpee todas las fuentes todos los días y alimente tableros, que pueden ser programados en python o Power BI" — solo fuentes con TOS que lo permita; GlobalData/Amadeus Feed/Brand24/ICCA full van por conector manual o API paga, nunca scraping que viole login/paywall.
- S2: Matriz base `matriz_bases_datos_bureau_medellin.xlsx` con 31 fuentes + pestaña `Plan Dashboard` con 30 KPIs con fórmulas es la especificación de KPIs.
- S3: KPIs deben calcularse en capa transform (Python/pandas) y quedar listos para Power BI sin DAX complejo.

## Tasks
- [x] T1 (S1,S2) Diseño + scaffold ETL + doc — route: inline — status: done — commit: 8c57bfb
- [x] T2 (S1) Extractores Tier-1 gratis diarios: Google Trends, UN Tourism, CITUR/Migración/Aerocivil CSV, Alerts RSS — route: inline — status: done — commit: f07c9f7
  Evidencia 27-oct: socrata_co (7wm8-w5ad 16k filas Medellín, 96sh-4v8d 50k, gb6w-ynu4 58k MDE/EOH) + dane_egit (IItrim2026, 67 filas) + trends 465 filas + gdelt 429-safe + alerts stub. Transform emite llegadas_medellin_nr=6.2M, top1 USA, share_top5=0.607, pax MDE 32M/33M.
  Pendientes honestos: DANE ENH (patrón URL distinto, dane_enh_ok=0), SITUR portal caído (manual mensual), GDELT 429 intermitente, CITUR directo (cubierto vía Socrata). — commit: eb7d3dc
- [x] T3 (S3) Transforms a modelo estrella + KPIs Plan Dashboard — route: inline — status: done — commit: 0249aa1 (alertas 421 menciones + CRM ejemplo: win_rate 0.6, noches 6685, derrama USD 1.46M, pipeline USD 582K)
- [x] T4a Pendientes automatización (28-oct): paginación Socrata (181k filas 96sh full), MEData 16 CSVs cableados (ocupación/tarifa/PITS/eventos, baseline 2023), GDELT single-query + backoff + carry-forward, EGIT parse por header (gasto II-2026 $149.530) — status: done — commit: f07c9f7
- [x] T4b (S1,S3) Load SQLite/Parquet + wiring Power BI + cron diario 06:00 — route: inline — status: done — 28-oct
  to_warehouse exporta 20 tablas a bureau.sqlite + parquet + 24 json en web/data; powerbi/README con tablas + refresh 07:00; cron 06:00 instalado.
- [x] T5 (S1) Conectores gated: Amadeus Developers, Brand24 trial, ICCA/Cvent manual — route: inline — status: done — 28-oct
  Stubs gated_*.py con SKIP sin key/archivo; manual/README con plantillas; daily.py los llama antes de transform.
  Nota ENH: DANE bloquea bots (search y deep-URLs devuelven página de error; anexos .xls viejos). ENH queda manual trimestral (5 min: descargar anexo de la página DANE) + MEData automático como baseline histórico. Ocupación fresca mensual: SITUR/MinCIT manual hasta que MEData se reactive.
  Gated: solo ingesta manual/API con key, nunca scraping login/paywall. Stubs en extract/gated_*.py que hacen skip si no hay key/archivo; plantillas en data/raw/manual/.
- [x] T6 Web estático + ECharts + destinos Colombia + línea Colmayor — route: inline — status: done — 28-oct — commit: 4e544a6/2ee7fbb/4706f31/58ba7d6
  web/index.html + export/to_json.py (24 JSON); tabs Destinos/Reciente/Países/Medellín/Desglose/Marca; YoY años completos; norm_pais case-insensitive.
- [x] T7 Boletín PDF automático — route: inline — status: done — 28-oct
  web/informe.html (plantilla A4 espejo TEC, bullets ejecutivos auto, 8 gráficos ECharts sin animación) + report/build_pdf.py (sirve web/, Playwright espera __REPORT_READY__, imprime A4 con fondo) → informes/boletin_YYYY-MM-DD.pdf. Verificado: texto completo + canvas render (gasto 26 pts, carga sin dip parcial).

## Log
- L1 (2026-10-27): "Ahora requiero que según estas fuentes, armemos un embudo automatizado que screpee todas las fuentes todos los días y alimente tableros, que pueden ser programados en python o Power BI"
- Decisión: nada de scraping a sitios con login/paywall (GlobalData, Amadeus Feed, Brand24 app, STR). Esos van como ingesta manual/API oficial. El embudo diario corre solo sobre 12 fuentes abiertas.
- Next: T2 extractores Tier-1.
