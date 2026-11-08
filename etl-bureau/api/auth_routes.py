"""Rutas de autenticación que cablean T1-T3 a HTTP (T4)."""
import hashlib
import html
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from api import security as sec
from backend import access, auth, db

router = APIRouter()


def _con():
    if not db.get_url():
        raise HTTPException(503, "sin BACKEND_DATABASE_URL")
    try:
        return db.connect()
    except Exception as e:
        raise HTTPException(503, f"sin conexion ({e})") from e


def _audit(con, email: str, evento: str, ok: bool) -> None:
    with con.cursor() as cur:
        cur.execute("INSERT INTO login_audit (email, evento, ok) VALUES (%s, %s, %s)",
                    (email, evento, ok))


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post("/auth/login")
def login(request: Request, email: str = Form(""), password: str = Form(""),
          totp: str = Form(""), csrf_token: str = Form("")):
    if not sec.check_csrf_token(csrf_token):
        raise HTTPException(403, "csrf inválido")
    con = _con()
    try:
        with con.cursor() as cur:
            row = cur.execute("SELECT id, pass_hash, totp_secret, estado FROM app_users"
                              " WHERE email = %s", (email,)).fetchone()
        if row and row[3] != "activo":
            _audit(con, email, "login_sin_acceso", False)
            raise HTTPException(403, "sin aprobación o sin acceso")
        if not sec.login_allowed(email, _ip(request)):
            raise HTTPException(429, "bloqueado temporalmente, probá más tarde")
        if not row or not auth.verify_password(row[1] or "", password) \
                or not auth.verify_totp(row[2] or "", totp):
            sec.register_failure(email, _ip(request))
            _audit(con, email, "login_fallido", False)
            raise HTTPException(401, "credenciales inválidas")
        sec.register_success(email, _ip(request))
        token = sec.new_session_token(row[0])
        digest = hashlib.sha256(token.encode()).hexdigest()
        expira = datetime.now(timezone.utc) + timedelta(days=sec.SESSION_DAYS)
        with con.cursor() as cur:
            cur.execute("INSERT INTO sessions (token_hash, user_id, expira)"
                        " VALUES (%s, %s, %s)", (digest, row[0], expira))
        _audit(con, email, "login_ok", True)
        con.commit()
        # El token va también en el body: el front Vercel (otro dominio) no recibe
        # la cookie y lo guarda como cookie propia tras login (tradeoff XSS documentado).
        resp = JSONResponse({"ok": True, "token": token})
        # Secure solo si el transporte es https (o AUTH_COOKIE_SECURE=1 tras proxy TLS).
        secure = request.url.scheme == "https" or os.environ.get("AUTH_COOKIE_SECURE") == "1"
        resp.set_cookie(sec.COOKIE, token, httponly=True, secure=secure,
                        samesite="lax", max_age=sec.SESSION_DAYS * 86400, path="/")
        return resp
    finally:
        con.close()


@router.get("/auth/csrf")
def csrf():
    # El front estatico no puede acunar HMAC sin el secreto: lo emite el server.
    # No expone nada: verificar no requiere secreto del lado lector.
    return {"csrf_token": sec.new_csrf_token()}


@router.get("/auth/yo")
def yo(user_id: str = Depends(sec.current_user)):
    return {"ok": True, "user_id": user_id}


@router.post("/auth/logout")
def logout(request: Request):
    token = request.cookies.get(sec.COOKIE, "")
    if token:
        con = _con()
        try:
            with con.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE token_hash = %s",
                            (hashlib.sha256(token.encode()).hexdigest(),))
            con.commit()
        finally:
            con.close()
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(sec.COOKIE, path="/")
    return resp


@router.post("/auth/solicitar")
def solicitar(request: Request, nombre: str = Form(""), email: str = Form(""),
              institucion: str = Form(""), motivo: str = Form(""),
              tipo: str = Form(""), csrf_token: str = Form("")):
    if not sec.check_csrf_token(csrf_token):
        raise HTTPException(403, "csrf inválido")
    con = _con()
    try:
        access.request_access(con, nombre, email, institucion, motivo, tipo)
        con.commit()
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        con.close()
    return {"ok": True, "estado": "pendiente"}


_PAGINA = ("<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"utf-8\">"
           "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
           "<title>{titulo} · Bureau</title><style>"
           "body{{font-family:Montserrat,Arial,sans-serif;background:#fff;color:#172139;margin:0}}"
           "header{{background:#172139;color:#fff;padding:20px 24px}}"
           "main{{max-width:560px;margin:24px auto;padding:0 16px}}"
           ".card{{background:#EEF1F5;border-left:6px solid #E9901E;border-radius:8px;"
           "padding:16px 18px;line-height:1.55}}"
           "button{{background:#E9901E;color:#fff;border:none;border-radius:20px;"
           "padding:10px 26px;font-weight:700;font-size:11pt;cursor:pointer;margin-top:10px}}"
           "</style></head><body><header><h1 style=\"margin:0;font-size:1.2rem\">"
           "Bureau · Aprobación de acceso</h1></header><main><div class=\"card\">"
           "{cuerpo}</div></main></body></html>")


def _pagina_aprobar(titulo: str, cuerpo: str) -> str:
    return _PAGINA.format(titulo=titulo, cuerpo=cuerpo)


@router.get("/auth/aprobar", response_class=HTMLResponse)
def aprobar_pagina(token: str = ""):
    con = _con()
    try:
        with con.cursor() as cur:
            row = cur.execute("SELECT email, nombre, institucion, motivo, tipo, estado"
                              " FROM access_requests WHERE token_aprobacion = %s",
                              (token,)).fetchone()
        if not row or row[5] != "pendiente":
            return HTMLResponse(_pagina_aprobar(
                "Enlace inválido", "<p>Este enlace ya fue usado o venció (72h).</p>"),
                status_code=400)
        email, nombre, inst, motivo, tipo, _ = row
        e = html.escape
        cuerpo = (f"<p><strong>{e(nombre)}</strong> ({e(email)}, {e(inst)}, {e(tipo)})"
                  f" solicita acceso.</p><p>Motivo: {e(motivo)}</p>"
                  f"<form method=\"post\" action=\"/auth/aprobar\">"
                  f"<input type=\"hidden\" name=\"token\" value=\"{e(token)}\">"
                  f"<button type=\"submit\">Aprobar acceso</button></form>")
        return HTMLResponse(_pagina_aprobar("Aprobar acceso", cuerpo))
    finally:
        con.close()


@router.post("/auth/aprobar", response_class=HTMLResponse)
def aprobar_ok(token: str = Form("")):
    con = _con()
    try:
        try:
            email = access.approve_request(con, token, "admin")
        except ValueError:
            return HTMLResponse(_pagina_aprobar(
                "Enlace inválido", "<p>Este enlace ya fue usado o venció (72h).</p>"),
                status_code=400)
        con.commit()
    finally:
        con.close()
    return HTMLResponse(_pagina_aprobar(
        "Acceso aprobado",
        f"<p>Acceso aprobado para <strong>{html.escape(email)}</strong>."
        " Ya puede activar su cuenta.</p>"))


def _qr_data_uri(uri: str) -> str:
    import base64
    import io

    import qrcode
    img = qrcode.make(uri, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@router.post("/auth/activar-mfa")
def activar_mfa(request: Request, email: str = Form(""), password: str = Form(""),
                csrf_token: str = Form(""), qr: str = Form("")):
    if not sec.check_csrf_token(csrf_token):
        raise HTTPException(403, "csrf inválido")
    con = _con()
    try:
        with con.cursor() as cur:
            row = cur.execute("SELECT aprobado FROM app_users WHERE email = %s",
                              (email,)).fetchone()
        if not row or not row[0]:
            raise HTTPException(403, "sin aprobación no se puede entrar")
        secret = auth.new_totp_secret()
        try:
            hashed = auth.hash_password(password)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        with con.cursor() as cur:
            cur.execute("UPDATE app_users SET pass_hash = %s, totp_secret = %s"
                        " WHERE email = %s", (hashed, secret, email))
        con.commit()
    finally:
        con.close()
    resp_body = {"ok": True, "otpauth_uri": auth.totp_uri(secret, email)}
    if qr:
        try:
            resp_body["qr_png"] = _qr_data_uri(resp_body["otpauth_uri"])
        except ImportError as e:
            raise HTTPException(400, "qr no disponible") from e
    return resp_body


@router.post("/auth/confirmar-mfa")
def confirmar_mfa(email: str = Form(""), totp: str = Form(""),
                  csrf_token: str = Form("")):
    if not sec.check_csrf_token(csrf_token):
        raise HTTPException(403, "csrf inválido")
    con = _con()
    try:
        with con.cursor() as cur:
            row = cur.execute("SELECT totp_secret, aprobado FROM app_users WHERE email = %s",
                              (email,)).fetchone()
        if not row or not row[1] or not auth.verify_totp(row[0] or "", totp):
            raise HTTPException(401, "verificación inválida")
        with con.cursor() as cur:
            cur.execute("UPDATE app_users SET estado = 'activo' WHERE email = %s", (email,))
        _audit(con, email, "activacion", True)
        con.commit()
    finally:
        con.close()
    return {"ok": True}
