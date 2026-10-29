# Feature: KPIs emisores, destinos y outbound

Objetivo: agregar KPIs escalares que respondan: qué países más visitan Colombia/Medellín, a qué destinos locales van, cuántos colombianos viajan. Hoy esa info vive en tablas (pais/destinos/salidas) pero no en kpis_historico. Branch: feature/bureau-etl-funnel.

## Specs
- S1: "esto no responde a los paises emisores, no se están contemplando los paises de exterior que más visitan colombia a qué destinos locales van, cuantos colombianos viajan" — verbatim usuario 28-oct.
- S2: ~12 escalares nuevos en kpis_historico desde PROC (no recomputar raw): emisores top1-5 + shares + mayor crecimiento; destino top + rank/share Medellín + mayor crecimiento; salidas totales + top destino + YoY.
- S3: Lectura defensiva de pais_dashboard.csv y destinos_dashboard.csv (columnas ano_ref dinámicas); SKIP individual si faltan; jamás tumba el run.
- S4: Sin frontend; las tablas siguen como drill-down, los escalares alimentan el dashboard.

## Tasks
- [x] T1 (S2,S3) `kpis_emisores()` en kpis.py + wire en run() (después de pai/des) — route: delegated worker — done 28-oct (18 claves desde PROC, try/except, merge en run())
- [x] T2 (S1,S4) Verificación: claves presentes + daily import OK — route: inline — done 28-oct (18/18 presentes; USA top 378K, El Salvador +168.9% YoY, Bogotá top, Medellín 24.45%, salidas 5.8M top USA 1.7M)

## Log
- L1 (2026-10-28): usuario pide KPIs de emisores, destinos locales y outbound colombiano.
- Next: T1.
