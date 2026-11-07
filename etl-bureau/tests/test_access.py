"""Workflow solicitud→aprobación→alta + invitados. TDD: RED primero (T3: S3,S4,S5)."""
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_URL = "host=/var/run/postgresql port=5433 dbname=bureau_test user=julian connect_timeout=10"
ADMIN = "consultor.ceitto@colmayor.edu.co"


def _con():
    from backend import access, auth
    con = psycopg.connect(TEST_URL, autocommit=True)
    auth.ensure_auth_schema(con)
    access.ensure_access_schema(con)
    with con.cursor() as cur:
        cur.execute("DELETE FROM approval_outbox")
        cur.execute("DELETE FROM access_requests")
        cur.execute("DELETE FROM sessions")
        cur.execute("DELETE FROM login_audit")
        cur.execute("DELETE FROM app_users")
    return con


def test_solicitud_crea_pendiente_y_no_entra():
    from backend import access, auth
    with _con() as con:
        tok = access.request_access(con, "Ana", "ana@colmayor.edu.co", "ColMayor", "ver tablero", "interno")
        assert tok
        assert auth.can_login(access.user_estado(con, "ana@colmayor.edu.co")) is False


def test_aprobar_sin_activar_sigue_sin_entrar():
    from backend import access, auth
    with _con() as con:
        tok = access.request_access(con, "Ana", "ana@colmayor.edu.co", "ColMayor", "ver", "interno")
        access.approve_request(con, tok, ADMIN)
        assert auth.can_login(access.user_estado(con, "ana@colmayor.edu.co")) is False


def test_activar_sin_aprobacion_falla():
    from backend import access
    with _con() as con:
        access.request_access(con, "Ana", "ana@colmayor.edu.co", "ColMayor", "ver", "interno")
        with pytest.raises(PermissionError):
            access.activate_user(con, "ana@colmayor.edu.co", "Password-larga-2026", "SECRETO")


def test_flujo_completo_entra():
    from backend import access, auth
    with _con() as con:
        tok = access.request_access(con, "Ana", "ana@colmayor.edu.co", "ColMayor", "ver", "interno")
        access.approve_request(con, tok, ADMIN)
        secret = auth.new_totp_secret()
        access.activate_user(con, "ana@colmayor.edu.co", "Password-larga-2026", secret)
        assert auth.can_login(access.user_estado(con, "ana@colmayor.edu.co")) is True


def test_solicitud_avisa_admin_o_outbox(monkeypatch):
    from backend import access
    monkeypatch.delenv("SMTP_HOST", raising=False)
    with _con() as con:
        res = access.request_access(con, "Luz", "luz@externa.org", "ONG", "ver", "invitado")
        assert res
        with con.cursor() as cur:
            row = cur.execute("SELECT payload FROM approval_outbox ORDER BY id DESC LIMIT 1").fetchone()
        assert row and ADMIN in row[0] and "luz@externa.org" in row[0]


def test_invitado_vencido_no_entra():
    from backend import access, auth
    with _con() as con:
        tok = access.request_access(con, "Luz", "luz@externa.org", "ONG", "ver", "invitado")
        access.approve_request(con, tok, ADMIN)
        access.activate_user(con, "luz@externa.org", "Password-larga-2026", auth.new_totp_secret())
        with con.cursor() as cur:
            cur.execute("UPDATE app_users SET expira_el = CURRENT_DATE - 1 WHERE email = 'luz@externa.org'")
        access.expire_guests(con)
        assert auth.can_login(access.user_estado(con, "luz@externa.org")) is False
