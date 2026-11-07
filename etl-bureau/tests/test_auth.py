"""Auth core login alta seguridad. TDD: RED primero (T1: S3,S7)."""
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_URL = "host=/var/run/postgresql port=5433 dbname=bureau_test user=julian connect_timeout=10"


def test_password_argon2id_y_politica_min12():
    from backend import auth
    assert not auth.password_ok("corta123"), "menos de 12 debe rechazar"
    h = auth.hash_password("Correcta-Horse-2026!")
    assert h != "Correcta-Horse-2026!" and "argon2" in h.lower()
    assert auth.verify_password(h, "Correcta-Horse-2026!")
    assert not auth.verify_password(h, "otra-password-larga")


def test_totp_roundtrip():
    from backend import auth
    secret = auth.new_totp_secret()
    uri = auth.totp_uri(secret, "ana@colmayor.edu.co")
    assert "otpauth://" in uri and "ana%40colmayor.edu.co" in uri
    import pyotp
    code = pyotp.TOTP(secret).now()
    assert auth.verify_totp(secret, code)
    assert not auth.verify_totp(secret, "000000")


def test_pendiente_no_entra_sin_aprobacion():
    from backend import auth
    assert auth.can_login("pendiente") is False, "S3: sin aprobación no entra"
    assert auth.can_login("rechazado") is False
    assert auth.can_login("activo") is True


def test_sesion_hmac_valida_y_tamper_falla():
    from backend import auth
    tok = auth.new_session_token("user-1", "secreto-test")
    assert auth.check_session_token(tok, "secreto-test") == "user-1"
    assert auth.check_session_token(tok + "x", "secreto-test") is None
    assert auth.check_session_token(tok, "otro-secreto") is None


def test_schema_auth_crea_tablas_aislado():
    from backend import auth
    with psycopg.connect(TEST_URL, autocommit=True) as con:
        auth.ensure_auth_schema(con)
        tablas = {r[0] for r in con.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            " AND tablename IN ('app_users','access_requests','sessions','login_audit')").fetchall()}
    assert {"app_users", "access_requests", "sessions", "login_audit"} <= tablas
