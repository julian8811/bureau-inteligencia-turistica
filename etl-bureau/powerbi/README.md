# Power BI — Bureau Medellín (3 páginas)

## Conexión
1. Get Data -> SQLite database -> `etl-bureau/data/processed/bureau.sqlite`, tabla `kpis_diario`
2. Get Data -> Folder -> `etl-bureau/data/processed/` (parquet) para detalle
3. Get Data -> Folder -> `etl-bureau/data/raw/` para auditoría de fuentes
4. Scheduled Refresh diario 07:00 COT (después del cron 06:00)

## Modelo
- `kpis_diario(fecha)` 1—* `fact` por fecha. Sin DAX complejo: los KPIs ya vienen calculados en Python.
- Medidas mínimas DAX:
  - `Win Rate = AVERAGE(kpis_diario[win_rate])`
  - `Derrama = SUM(kpis_diario[derrama_mice])`
  - `Sentimiento = AVERAGE(kpis_diario[sentimiento_neto])`

## Páginas (espejo Plan Dashboard Excel)
1. **Reuniones:** win rate, noches, derrama, pipeline, ICCA (tabla manual anual)
2. **Vacacional:** llegadas (CITUR/Migración CSV), estadía, gasto, ocupación, Trends
3. **Marca:** menciones, sentimiento neto, share, engagement

## Gated (manual mensual)
Pegar en `data/raw/manual/`: `crm.xlsx` (RFP/eventos), reportes GlobalData comprados, CSV Brand24 trial.
El transform los absorbe solo si existen.
