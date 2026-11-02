# Feature: Classify backend LLM (Groq free)

Objetivo: paso `classify` en el ETL que clasifica titulares del día (alerts + prensa) con un LLM gratis en la nube y guarda `data/raw/<hoy>/clasificacion_llm.csv`. Sin key → SKIP honesto. Branch: feature/bureau-etl-funnel.

## Specs
- S1: "implementa el backend, cuales son las mejores opciones gratis?" — verbatim usuario 28-oct.
- S2: Groq free (llama-3.3-70b-versatile, 30 RPM/1000 RPD, sin tarjeta) vía endpoint OpenAI-compatible con `requests` (sin deps nuevas). Key en env `GROQ_API_KEY`, nunca en repo ni en chat.
- S3: Lotes de 50 titulares, temp 0, JSON estricto {categoria, sentimiento, topico}; 429 → backoff 60s + 1 reintento por lote; timeout 90s; jamás tumba el daily.
- S4: Sin frontend (decisión 28-oct): el CSV lo absorbe transform/load y se muestra en el HTML existente cuando se diseñe el dashboard.

## Tasks
- [x] T1 (S2,S3) `classify/llm_classify.py` + wire en daily.py (después de kpis, antes de to_warehouse) — route: inline — done 28-oct
- [x] T2 (S1,S4) Verificación: compile + import + run sin key (SKIP limpio) — route: inline — done 28-oct (COMPILE_OK, daily import OK, SKIP sin archivo ni excepción)

## Log
- L1 (2026-10-28): "implementa el backend, cuales son las mejores opciones gratis?"
- Decisión 28-oct: Groq > Gemini (503s) > OpenRouter (50/día) > Cerebras (trial). classify escribe raw; PROC/dashboard lo consumen después.
- Next: T1.
