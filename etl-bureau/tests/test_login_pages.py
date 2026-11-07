"""Páginas login con línea gráfica. TDD: RED primero (T2: S1,S5,S6)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PAGES = ("login.html", "solicitar.html", "pendiente.html", "activar-mfa.html")


def _build(tmp_path):
    from dashboard import build_login
    return build_login.run(str(tmp_path))


def test_genera_cuatro_paginas(tmp_path):
    out = _build(tmp_path)
    for p in PAGES:
        assert (Path(out) / p).exists(), p


def test_mismo_css_que_tablero(tmp_path):
    from dashboard.build_html import CSS
    out = _build(tmp_path)
    html = (Path(out) / "login.html").read_text(encoding="utf-8")
    assert CSS.strip() in html, "S6: el login debe reusar el CSS exacto del tablero"


def test_sin_script_y_con_marca(tmp_path):
    out = _build(tmp_path)
    for p in PAGES:
        html = (Path(out) / p).read_text(encoding="utf-8")
        assert "<script" not in html.lower(), p
        for token in ("#172139", "#E9901E", "Montserrat",
                      "logo_colmayor_navy.png", "Vigilada MinEducación"):
            assert token in html, (p, token)


def test_login_pide_password_y_totp(tmp_path):
    out = _build(tmp_path)
    html = (Path(out) / "login.html").read_text(encoding="utf-8")
    assert 'method="post"' in html.lower()
    assert 'name="password"' in html
    assert 'name="totp"' in html or 'name="otp"' in html


def test_solicitud_y_pendiente_nombran_canal_aprobacion(tmp_path):
    out = _build(tmp_path)
    sol = (Path(out) / "solicitar.html").read_text(encoding="utf-8")
    for field in ('name="nombre"', 'name="email"', 'name="motivo"', 'name="tipo"'):
        assert field in sol, field
    pend = (Path(out) / "pendiente.html").read_text(encoding="utf-8")
    assert "consultor.ceitto@colmayor.edu.co" in pend, "S3: sin aprobación no se entra"


def test_form_css_con_estados(tmp_path):
    out = _build(tmp_path)
    html = (Path(out) / "login.html").read_text(encoding="utf-8")
    for token in ("focus-visible", ".error", "prefers-reduced-motion"):
        assert token in html, token
