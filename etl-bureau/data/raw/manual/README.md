# Manual gated — pegar archivos aqui (nunca scraping login/paywall)

- `crm.xlsx` — RFP/eventos Bureau. Columnas: estado, asistentes, gasto_prom_usd,
  estadia_noches, valor_rfp_usd, prob. Ya existe ejemplo.
- `brand24*.csv` — export trial Brand24 (fecha,titulo,url,sentimiento,alcance).
- `amadeus*` — CSV comprado o respuesta API guardada.
- `icca*.xlsx/csv` — ranking anual ICCA. `cvent*.xlsx/csv` — export Cvent.
- `situr*.xlsx/csv` — SITUR Antioquia mensual (portal caido, carga manual).
- DANE ENH trimestral: descargar anexo .xls de la pagina DANE y pegar como
  `dane_enh_YYYY-Tn.xlsx` (el extractor lo detecta si existe).

El daily (`orchestration/daily.py`) llama a `gated_*.run()` que hacen SKIP
si no hay archivo/key. El transform absorbe lo que exista.
