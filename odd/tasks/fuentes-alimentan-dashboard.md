# Feature: Verificar que las fuentes alimenten el dashboard diario

Objetivo: probar de punta a punta que las fuentes del ETL terminan en el dashboard diario (local + tableros-bureau Vercel), con datos de hoy.

## Specs
- S1: "debemos mirar que las fuentes si alimenten el dashboard diario" — verbatim usuario 01-nov-2026.
- S2: Cadena: extract → transform → to_warehouse (sqlite+parquet+web/data) → build_html (dashboard/index.html) → tableros_bureau_llm (adapter) → publicar (push + PR tableros-bureau).
- S3: Criterio: PROC/web/data con fecha de hoy, adapter ok 3/3, dashboard local regenerado, archivos para Vercel listos. Sin tumbar nada: cada paso ya tiene SKIP/carry.
- S4: Informe LLM y PDFs solo si hay GROQ (hay en env); si falla, se reporta y no bloquea.

## Tasks
- [x] T1 (S2) Correr daily completo end-to-end — route: inline (background, ~15-25 min) — done 02-nov (~6m15s, exit 0)
- [x] T2 (S3) Verificar PROC/web/adapter/dashboard + archivos Vercel — route: inline — done 02-nov
- [x] T3 Cerrar con tabla fuente→panel y pendientes — route: inline — done 02-nov

## Log
- L1 (2026-11-01): usuario pide verificar alimentación diaria real del dashboard.
- L2 (2026-11-01): daily full OK. PROC hoy (kpis_2026-11-01, histórico 4 días), web/data kpis+paises frescos, adapter 3/3 ok (788+6+9), dashboard local + PDFs de hoy. Informe LLM de hoy INVALID (cifra 149.53 sin fuente) -> web/data/informe_llm.json sigue en corte 31-oct. Publicar SKIP x2 (git fetch timeout + gh HTTP 499) -> Vercel sin actualizar hoy. Backend Supabase ok día=2026-11-01.
- L3 (2026-11-02): daily 02-nov exit 0 ~6m15s. PROC kpis_2026-11-02 + historico 5 dias, sqlite 22 tablas, web/data 25 json 09:28, export/tableros_bureau 4 archivos 09:28 (adapter 788+6+10 secciones, manifiesto ok), dashboard/index.html 43KB fecha 02-nov. Tanda-1: fx_cop 1 fila COP=3201.17, ensemble 7 filas/39 members, tieredtravel 1 fila (0 match Medellin, 236 atracciones), airportmiles 0, emisores 0 (404 primary+fallback). SKIP honestos: ticketmaster/opentripmap/classify/backend/informe sin keys, transform 7 gated sin CSV, pdfs sin chromium, actualizar_tableros 401 Bad credentials. web/data/informe_llm.json sigue 01-nov (no regenera sin LLM). push_export ok 4 archivos pero sin PR a Vercel.
- L4 (2026-11-02): reintento actualizar_tableros con token temporal del usuario → ok, cambios 1 (commit 58fdfa1 sync + PR mergeado). data/open fresco 09:36. gh logout hecho, credencial fuera del disco. Pendiente: usuario revoca token.
