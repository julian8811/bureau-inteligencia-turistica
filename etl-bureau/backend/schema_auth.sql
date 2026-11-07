CREATE TABLE IF NOT EXISTS app_users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  nombre TEXT NOT NULL DEFAULT '',
  tipo TEXT NOT NULL DEFAULT 'invitado' CHECK (tipo IN ('interno', 'invitado', 'admin')),
  estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'activo', 'rechazado', 'expirado')),
  pass_hash TEXT NOT NULL DEFAULT '',
  totp_secret TEXT NOT NULL DEFAULT '',
  expira_el DATE NULL,
  creado TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS access_requests (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  nombre TEXT NOT NULL DEFAULT '',
  institucion TEXT NOT NULL DEFAULT '',
  motivo TEXT NOT NULL DEFAULT '',
  tipo TEXT NOT NULL DEFAULT 'invitado' CHECK (tipo IN ('interno', 'invitado')),
  estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
  token_aprobacion TEXT UNIQUE NOT NULL,
  creado TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
  expira TIMESTAMPTZ NOT NULL,
  creado TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS login_audit (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL DEFAULT '',
  evento TEXT NOT NULL,
  ok BOOLEAN NOT NULL,
  ip TEXT NOT NULL DEFAULT '',
  creado TIMESTAMPTZ NOT NULL DEFAULT now()
);
