# Feature: Dashboard HTML puro (reemplazo Streamlit)

Objetivo: eliminar Streamlit/Plotly como tecnología de visualización y generar un tablero estático en HTML + CSS puro, imprimible, sin servidor Python ni JS pesado. Branch: feature/bureau-etl-funnel. Runner: `python etl-bureau/dashboard/build_html.py` dentro del daily/load.
Estrategia delivery: single-pr (forecast <400 líneas por slice).

## Specs
- S1: "Requiero cambiar la tecnologia del cómo se muestran los datos, no me vgusta la tecnologia actual" — verbatim usuario 28-oct.
- S2: Reemplazar "Dashboard Streamlit" (`etl-bureau/dashboard/app.py`, 158 líneas + tab Por país) — respuesta usuario.
- S3: Llevar a "HTML + CSS puro" ("Reporte imprimible sin JS pesado") — respuesta usuario. Sin `<script>`, sin Streamlit, sin Plotly, solo tablas + CSS Colmayor + `@media print`.
- S4: Paridad mínima: 4 secciones espejo de los 4 tabs (Reuniones, Vacacional, Marca, Por país) con los mismos KPIs del `kpis_historico.csv` + tablas top10/ranking desde PROC/RAW.

## Tasks
- [x] T1 (S3,S4) Generador `dashboard/build_html.py` → `dashboard/index.html` puro — route: inline — done 28-oct
- [x] T2 (S2,S3) Wire al daily/load + deprecate Streamlit (requirements + app.py) — route: inline — done 28-oct (daily llama build_html.run; app.py → app_streamlit_legacy.py; requirements sin streamlit/plotly)
- [x] T3 (S4) Verificación: build OK, sin `<script>`, 4 secciones + tablas con datos — route: inline — done 28-oct (11 KPIs, 5 tablas, daily import OK)

## Log
- L1 (2026-10-28): "Requiero cambiar la tecnologia del cómo se muestran los datos, no me vgusta la tecnologia actual"
- Decisión 28-oct: reemplazar solo Streamlit; `web/` ECharts y PBIT quedan como están. HTML puro = cero JS, CSS inline en el archivo, logo local.
- Next: T1 generador.
