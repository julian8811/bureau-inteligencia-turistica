-- Backend post-embudo LLM (Postgres 14+, vale Supabase/Neon/local).
-- Idempotencia por día: el writer borra el día y re-inserta.
CREATE TABLE IF NOT EXISTS clasificacion_llm (
  dia DATE NOT NULL,
  titulo TEXT NOT NULL,
  medio TEXT,
  fecha TEXT,
  link TEXT,
  categoria TEXT,
  sentimiento TEXT,
  topico TEXT,
  modelo TEXT,
  PRIMARY KEY (dia, titulo, medio)
);
CREATE TABLE IF NOT EXISTS marca_llm (
  dia DATE NOT NULL,
  categoria TEXT NOT NULL,
  n INTEGER,
  share DOUBLE PRECISION,
  sent_net DOUBLE PRECISION,
  top_topico TEXT,
  PRIMARY KEY (dia, categoria)
);
CREATE TABLE IF NOT EXISTS informes (
  corte TEXT NOT NULL,
  seccion TEXT NOT NULL,
  titulo TEXT,
  bullets JSONB,
  cifras JSONB,
  creado TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (corte, seccion)
);
