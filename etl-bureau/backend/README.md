# Backend post-embudo LLM (Opción B: Postgres gestionado + API)

Guarda la salida del embudo LLM en Postgres en vez de solo archivos:
`clasificacion_llm` (titulares del día), `marca_llm` (agregado por categoría),
`informes` (secciones redactadas). Todo idempotente por día/corte: re-correr
no duplica. Sin URL o sin conexión → SKIP honesto, jamás tumba el daily.

## 1. Crear la base (lo hace el humano, una vez)

**Supabase** (o **Neon**, los pasos son los mismos):
1. Crear proyecto gratis → copiar la **connection string** (URI Postgres).
   - Supabase: Settings → Database → Connection string (usar la de **pooler**, puerto 6543, para el ETL alcanza la directa).
   - Neon: Dashboard → Connect → copiar `DATABASE_URL` (usar la pooled si el ETL corre serverless).
2. Abrir el SQL editor y pegar todo `etl-bureau/backend/schema.sql` → Run.
3. Guardar la URI como secreto del entorno donde corre el daily:
   `export BACKEND_DATABASE_URL='postgresql://...'`
   (también vale `DATABASE_URL`; `BACKEND_` tiene prioridad).

## 2. Desarrollo local

```bash
createdb bureau_llm
export BACKEND_DATABASE_URL='postgresql:///bureau_llm'
psql "$BACKEND_DATABASE_URL" -f etl-bureau/backend/schema.sql
python3 -m pytest etl-bureau/tests/   # writer + api + snapshot (usan bureau_test local)
```

## 3. Escritura (daily)

`orchestration/daily.py` corre `backend_writer.run()` después de `to_warehouse`:
retorna `{"status": "ok"|"skip", "dia", "marca", "clasificacion"}`.

## 4. Lectura (API)

```bash
uvicorn api.main:app --port 8080   # desde etl-bureau/
```

- `GET /health` → `{"db": "ok"}`
- `GET /marca?dia=2026-10-29` (vacío = último día)
- `GET /clasificacion?dia=&categoria=&limit=200`
- `GET /informes?corte=` (vacío = último corte)

Sin URL la API responde 503 honesto (salvo `/health`, que reporta `sin_url`).

## 5. Consumo desde tableros-bureau (Vercel estático)

Vercel no abre conexiones Postgres directas desde el JS del tablero. Dos vías:

- **En vivo:** `fetch('https://TU-API/marca')` (hay que hostear el API, ej. Railway/Fly/Render).
- **Archivos (recomendado):** `python3 -m backend.export_snapshot` genera
  `export/backend_snapshot/{marca_llm.json,informes.json}` listos para PR
  a `data/open/` de tableros-bureau, igual que el adapter actual.
