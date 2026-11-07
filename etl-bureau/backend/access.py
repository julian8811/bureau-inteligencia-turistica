"""Workflow solicitud→aprobación→alta + invitados (T3: S3,S4).

S3: sin aprobación del admin no se entra (gate en activate_user + can_login).
Aviso al admin por SMTP si hay SMTP_HOST, si no a approval_outbox (bandeja).
"""
import http.client
import json
import os
import secrets
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage

from backend import auth

APPROVAL_ADMIN = "consultor.ceitto@colmayor.edu.co"
APPROVAL_TTL_HOURS = 72
GUEST_DEFAULT_DAYS = 90
# Cloudflare delante de api.resend.com bloquea UAs de bot (1010): UA propio neutro.
EMAIL_UA = "bureau-etl/1.0"  # UAs de bot son bloqueadas (Cloudflare 1010): UA propio neutro


def ensure_access_schema(con) -> None:
    # Solo DDL literal; sin input de usuario ni interpolación.
    with con.cursor() as cur:
        cur.execute("ALTER TABLE app_users ADD COLUMN IF NOT EXISTS aprobado BOOLEAN NOT NULL DEFAULT FALSE")
        cur.execute("ALTER TABLE access_requests ADD COLUMN IF NOT EXISTS expira TIMESTAMPTZ NULL")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS approval_outbox ("
            "id SERIAL PRIMARY KEY, payload TEXT NOT NULL, "
            "creado TIMESTAMPTZ NOT NULL DEFAULT now())"
        )


def _audit(con, email: str, evento: str, ok: bool) -> None:
    with con.cursor() as cur:
        cur.execute(
            "INSERT INTO login_audit (email, evento, ok) VALUES (%s, %s, %s)",
            (email, evento, ok),
        )


def _send_resend(admin: str, subject: str, body: str) -> None:
    key = os.environ.get("EMAIL_API_KEY", "").strip()
    if not key:
        raise RuntimeError("sin EMAIL_API_KEY")
    sender = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
    payload = json.dumps({"from": sender, "to": [admin],
                          "subject": subject, "text": body}).encode()
    conn = http.client.HTTPSConnection("api.resend.com", timeout=15)
    try:
        conn.request("POST", "/emails", body=payload,
                     headers={"Authorization": "Bearer " + key,
                              "Content-Type": "application/json",
                              "Accept": "application/json",
                              "User-Agent": EMAIL_UA})
        r = conn.getresponse()
        r.read()
        if r.status >= 300:
            raise RuntimeError(f"resend status {r.status}")
    finally:
        conn.close()


def _send_brevo(admin: str, subject: str, body: str) -> None:
    key = os.environ.get("BREVO_API_KEY", "").strip()
    if not key:
        raise RuntimeError("sin BREVO_API_KEY")
    sender = os.environ.get("BREVO_FROM", APPROVAL_ADMIN)
    payload = json.dumps({"sender": {"email": sender, "name": "Bureau"},
                          "to": [{"email": admin}],
                          "subject": subject, "textContent": body}).encode()
    conn = http.client.HTTPSConnection("api.brevo.com", timeout=15)
    try:
        conn.request("POST", "/v3/smtp/email", body=payload,
                     headers={"api-key": key,
                              "Content-Type": "application/json",
                              "Accept": "application/json",
                              "User-Agent": EMAIL_UA})
        r = conn.getresponse()
        r.read()
        if r.status >= 300:
            raise RuntimeError(f"brevo status {r.status}")
    finally:
        conn.close()


def _notify_admin(con, subject: str, body: str) -> dict:
    admin = os.environ.get("APPROVAL_ADMIN_EMAIL", APPROVAL_ADMIN)
    text = f"Para: {admin}\nAsunto: {subject}\n\n{body}"
    try:
        _send_resend(admin, subject, body)
        return {"status": "sent", "to": admin, "via": "resend"}
    except Exception as e:
        print(f"[access][WARN] resend no disponible ({e}), pruebo brevo")
    try:
        _send_brevo(admin, subject, body)
        return {"status": "sent", "to": admin, "via": "brevo"}
    except Exception as e:
        print(f"[access][WARN] brevo no disponible ({e}), pruebo smtp")
    host = os.environ.get("SMTP_HOST", "").strip()
    if host:
        try:
            msg = EmailMessage()
            msg["From"] = os.environ.get("SMTP_FROM", admin)
            msg["To"] = admin
            msg["Subject"] = subject
            msg.set_content(body)
            port = int(os.environ.get("SMTP_PORT", "587"))
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.starttls()
                if os.environ.get("SMTP_USER"):
                    smtp.login(os.environ.get("SMTP_USER", ""),
                               os.environ.get("SMTP_PASS", ""))
                smtp.send_message(msg)
            return {"status": "sent", "to": admin}
        except Exception as e:
            print(f"[access][WARN] smtp fallo, va a outbox ({e})")
    with con.cursor() as cur:
        cur.execute("INSERT INTO approval_outbox (payload) VALUES (%s)", (text,))
    return {"status": "queued", "to": admin}


def request_access(con, nombre: str, email: str, institucion: str,
                   motivo: str, tipo: str) -> str:
    if tipo not in ("interno", "invitado"):
        raise ValueError("tipo debe ser interno o invitado")
    if "@" not in (email or ""):
        raise ValueError("email inválido")
    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(hours=APPROVAL_TTL_HOURS)
    exp_date = date.today() + timedelta(days=GUEST_DEFAULT_DAYS) if tipo == "invitado" else None
    with con.cursor() as cur:
        cur.execute(
            "INSERT INTO access_requests (email, nombre, institucion, motivo, tipo,"
            " token_aprobacion, expira) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (email, nombre, institucion, motivo, tipo, token, expira),
        )
        cur.execute(
            "INSERT INTO app_users (id, email, nombre, tipo, expira_el)"
            " VALUES (%s, %s, %s, %s, %s)"
            " ON CONFLICT (email) DO UPDATE SET nombre = EXCLUDED.nombre,"
            " tipo = EXCLUDED.tipo",
            ("u_" + secrets.token_hex(8), email, nombre, tipo, exp_date),
        )
    base = os.environ.get("APPROVAL_BASE_URL", "http://localhost:8080")
    _notify_admin(con, f"Solicitud de acceso: {email}",
                  f"{nombre} ({email}, {institucion}, {tipo}) solicita acceso.\n"
                  f"Motivo: {motivo}\nAprobar: {base}/auth/aprobar?token={token}\n"
                  f"Expira en {APPROVAL_TTL_HOURS}h. Sin aprobación no se puede entrar.")
    _audit(con, email, "solicitud", True)
    return token


def approve_request(con, token: str, admin_email: str) -> str:
    with con.cursor() as cur:
        row = cur.execute(
            "SELECT email, estado, expira FROM access_requests"
            " WHERE token_aprobacion = %s", (token,)).fetchone()
        if not row:
            raise ValueError("token desconocido")
        email, estado, expira = row
        now = datetime.now(timezone.utc)
        if estado != "pendiente" or (expira is not None and expira < now):
            raise ValueError("solicitud no aprobable (usada o vencida)")
        cur.execute("UPDATE access_requests SET estado = 'aprobada'"
                    " WHERE token_aprobacion = %s", (token,))
        cur.execute("UPDATE app_users SET aprobado = TRUE WHERE email = %s", (email,))
    _audit(con, email, f"aprobada_por_{admin_email}", True)
    return email


def activate_user(con, email: str, password: str, totp_secret: str) -> None:
    with con.cursor() as cur:
        row = cur.execute("SELECT aprobado FROM app_users WHERE email = %s",
                          (email,)).fetchone()
        if not row:
            raise ValueError("usuario desconocido")
        if not row[0]:
            _audit(con, email, "activacion_sin_aprobacion", False)
            raise PermissionError("sin aprobación del admin no se puede entrar")
        if not totp_secret:
            raise ValueError("totp requerido")
        cur.execute("UPDATE app_users SET pass_hash = %s, totp_secret = %s,"
                    " estado = 'activo' WHERE email = %s",
                    (auth.hash_password(password), totp_secret, email))
    _audit(con, email, "activacion", True)


def user_estado(con, email: str) -> str:
    with con.cursor() as cur:
        row = cur.execute("SELECT estado FROM app_users WHERE email = %s",
                          (email,)).fetchone()
    return row[0] if row else ""


def expire_guests(con) -> int:
    with con.cursor() as cur:
        cur.execute("UPDATE app_users SET estado = 'expirado' WHERE tipo = 'invitado'"
                    " AND estado = 'activo' AND expira_el IS NOT NULL"
                    " AND expira_el < CURRENT_DATE")
        n = cur.rowcount
    return n
