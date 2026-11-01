# Power BI — Bureau Medellín (3 páginas)

## Conexión (T4b)
1. Get Data -> SQLite database -> `etl-bureau/data/processed/bureau.sqlite`:
   - `kpis_diario` (una fila por fecha, KPIs MICE + demanda + marca)
   - `pais` (pais_dashboard: med/nac/aer/sal por pais + YoY + share)
   - `destinos` (destinos_dashboard: ranking Colombia + YoY + share)
   - `ult3m_pais` (trimestre movil por pais)
   - `desglose_*` (genero, rutas, aerolineas, carga, PITS, alojamiento, etc.)
2. Get Data -> Folder -> `etl-bureau/data/processed/` (parquet, mismo contenido)
3. Get Data -> Folder -> `etl-bureau/data/raw/` para auditoría de fuentes
4. Scheduled Refresh diario 07:00 COT (después del cron 06:00 que corre `orchestration/daily.py`)

Cron: `bash etl-bureau/orchestration/cron_install.sh` instala
`0 6 * * * /usr/bin/python3 .../daily.py >> .../logs/cron.log 2>&1`.
El load regenera sqlite + parquet + `web/data/*.json` en cada corrida.

## Modelo
- `kpis_diario(fecha)` 1—* `fact` por fecha. Sin DAX complejo: los KPIs ya vienen calculados en Python.
- Relaciones: `pais[pais]` 1—* `ult3m_pais[pais]`, `destinos[ciudad]` suelta (ranking).
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
