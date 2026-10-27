# Feature: Embudo automatizado Bureau Medellín — ETL diario + Power BI

Objetivo: scrapear/extraer a diario solo fuentes permitidas (APIs oficiales, CSV, RSS, HTML público) y alimentar 3 tableros (Reuniones / Vacacional / Marca). Branch: feature/bureau-etl-funnel. Runner: Python 3.11 + cron/systemd + Power BI DirectQuery/Scheduled Refresh.
Estrategia delivery: single-pr (forecast <400 líneas por slice).

## Specs
- S1: "armemos un embudo automatizado que screpee todas las fuentes todos los días y alimente tableros, que pueden ser programados en python o Power BI" — solo fuentes con TOS que lo permita; GlobalData/Amadeus Feed/Brand24/ICCA full van por conector manual o API paga, nunca scraping que viole login/paywall.
- S2: Matriz base `matriz_bases_datos_bureau_medellin.xlsx` con 31 fuentes + pestaña `Plan Dashboard` con 30 KPIs con fórmulas es la especificación de KPIs.
- S3: KPIs deben calcularse en capa transform (Python/pandas) y quedar listos para Power BI sin DAX complejo.

## Tasks
- [x] T1 (S1,S2) Diseño + scaffold ETL + doc — route: inline — status: done — commit: pendiente
- [ ] T2 (S1) Extractores Tier-1 gratis diarios: Google Trends, UN Tourism, CITUR/Migración/Aerocivil CSV, Alerts RSS — route: inline
- [ ] T3 (S3) Transforms a modelo estrella + KPIs Plan Dashboard — route: inline
- [ ] T4 (S1,S3) Load a SQLite/Parquet + wiring Power BI + scheduler diario — route: inline
- [ ] T5 (S1) Conectores gated: Amadeus Developers, Brand24 trial, ICCA/Cvent manual — route: inline

## Log
- L1 (2026-10-27): "Ahora requiero que según estas fuentes, armemos un embudo automatizado que screpee todas las fuentes todos los días y alimente tableros, que pueden ser programados en python o Power BI"
- Decisión: nada de scraping a sitios con login/paywall (GlobalData, Amadeus Feed, Brand24 app, STR). Esos van como ingesta manual/API oficial. El embudo diario corre solo sobre 12 fuentes abiertas.
- Next: T2 extractores Tier-1.
