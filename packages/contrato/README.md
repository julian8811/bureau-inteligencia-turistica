# Contrato tableros-bureau (T4)

Fuente de verdad del intercambio ETL → front. Sin mover archivos vivos:
no se toca `apps/etl/export/tableros_bureau/` (lo escribe el daily) ni
`apps/tableros/data/open/` (lo sirve Vercel). Este paquete solo fija el
formato y verifica que ambas copias coincidan.

## Piezas compartidas (SHA verificado 2026-11-01)

| id | ETL escribe | front sirve | estado |
|----|-------------|-------------|--------|
| `informe_llm` | `apps/etl/export/tableros_bureau/informe_llm.json` | `apps/tableros/data/open/informe_llm.json` | `sha256 9d479f5256c72b006936c6203b6854356e2a732f198d32f4d0b44913be1249f3` en ambas (2026-11-01) |
| `paises_2025_2026` | `apps/etl/export/tableros_bureau/paises_2025_2026.json` | `apps/tableros/data/open/bureau_paises_2025_2026.json` | mismo grano anual, validar `n` contra manifiesto |
| `marca_llm_2025_2026` | `apps/etl/export/tableros_bureau/marca_llm_2025_2026.json` | `apps/tableros/data/open/bureau_marca_llm.json` | idem |

Manifiestos: `manifiesto_bureau.json` (ETL) y `manifiesto.json` (front)
describen `piezas[{archivo,id,estado,n}]`. Regla: `estado: ok` exige que
el archivo exista y `n>0`; `SKIP` solo con justificación (sin key/archivo).

## Validación

`sh packages/contrato/check.sh` — compara SHA de `informe_llm.json`
entre ambas copias y valida `piezas[].n` contra los manifiestos.
Sale 0 si todo coincide, 1 con el mismatch impreso.
