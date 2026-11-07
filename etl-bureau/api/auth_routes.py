"""Rutas de autenticación que cablean T1-T3 a HTTP (T4)."""
import hashlib
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse

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


@router.get("/auth/aprobar")
def aprobar(token: str = ""):
    con = _con()
    try:
        try:
            email = access.approve_request(con, token, "admin")
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        con.commit()
    finally:
        con.close()
    return {"ok": True, "email": email}


@router.post("/auth/activar-mfa")
def activar_mfa(request: Request, email: str = Form(""), password: str = Form(""),
                csrf_token: str = Form("")):
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
    return {"ok": True, "otpauth_uri": auth.totp_uri(secret, email)}


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
