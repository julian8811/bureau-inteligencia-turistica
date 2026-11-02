# Embudo Bureau Medellín — ETL diario + Power BI
Ver `odd/tasks/bureau-etl-funnel.md` (spec + log).

## Regla legal (importante)
NO scrapear nada detrás de login/paywall: GlobalData, Amadeus Booking Feed, Brand24 app, STR, ICCA full.
Esos van por carga manual (CSV que compra el Bureau) o API oficial con key.
El runner diario solo toca fuentes abiertas (Tier-1).

## Estructura
- `config/sources.yml` — qué se corre diario vs manual
- `extract/` — un script por fuente Tier-1, guarda `data/raw/YYYY-MM-DD/fuente.*` (P1: `dane_ema` mensual DANE, `ticketmaster_eventos` con `TICKETMASTER_KEY`, `opensky_mde` en vivo sin key)
- `transform/kpis.py` — pandas → modelo estrella + 30 KPIs del Plan Dashboard
- `load/to_warehouse.py` — Parquet + SQLite `data/processed/bureau.duckdb/sqlite`
- `orchestration/daily.py` — corre todo, loggea, sale 0 aunque una fuente falle
- `powerbi/` — cómo conectar Power BI al warehouse

## Uso
```bash
pip install -r etl-bureau/requirements.txt
python etl-bureau/orchestration/daily.py
# Power BI: Get Data -> SQLite / Parquet folder -> refresh programado diario
```
Cron diario 06:00 COT:
`0 6 * * * /usr/bin/python3 /home/julian/Bureau/etl-bureau/orchestration/daily.py >> /home/julian/Bureau/etl-bureau/logs/cron.log 2>&1`
