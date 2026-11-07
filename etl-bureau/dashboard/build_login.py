"""Generador páginas de acceso con la línea gráfica exacta del tablero (T2: S6).

Reusa el CSS de build_html sin copiarlo: mismo navy/orange/Montserrat,
HTML puro sin <script>. Uso: python etl-bureau/dashboard/build_login.py [dir]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard.build_html import CSS as TABLERO_CSS  # noqa: E402  (S6: CSS idéntico)

OUT_DEFAULT = Path(__file__).resolve().parent

FORM_CSS = (
    ".card{background:#EEF1F5;border-left:6px solid var(--orange);border-radius:8px;"
    "padding:18px 20px;max-width:520px;margin:22px auto}"
    "label{display:block;font-size:10pt;font-weight:700;margin:10px 0 4px}"
    "input,select,textarea{width:100%;padding:8px 10px;border:2px solid var(--navy);"
    "border-radius:6px;font-size:11pt;font-family:inherit;color:var(--navy);background:#fff}"
    "button{background:var(--orange);color:#fff;border:none;border-radius:20px;"
    "padding:10px 26px;font-weight:700;font-size:11pt;margin-top:14px;cursor:pointer}"
    ".alt{text-align:center;margin-top:12px;font-size:10pt}"
)

APPROVAL_MAIL = "consultor.ceitto@colmayor.edu.co"


def _shell(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · Bureau Medellín</title>
<style>{TABLERO_CSS}{FORM_CSS}</style>
</head>
<body>
<header>
<img src="assets/logo_colmayor_navy.png" alt="I.U. Colegio Mayor de Antioquia">
<h1>Inteligencia Turística · Medellín y Antioquia</h1>
<p>I.U. Colegio Mayor de Antioquia · Acceso restringido · ETL diario Python · HTML puro sin JS</p>
</header>
<main>
<h2>{title}</h2>
{body}
<p class="src">El acceso requiere aprobación del administrador. Sin aprobación no se puede entrar.</p>
<div class="foot">I.U. Colegio Mayor de Antioquia · Vigilada MinEducación · Acceso institucional e invitados.</div>
</main>
</body>
</html>"""


def _login() -> str:
    return _shell("Entrar", """<div class="card"><form method="post" action="/auth/login">
<input type="hidden" name="csrf_token" value="">
<label for="email">Correo institucional</label>
<input id="email" name="email" type="email" required autocomplete="username">
<label for="password">Contraseña (mínimo 12 caracteres)</label>
<input id="password" name="password" type="password" required minlength="12" autocomplete="current-password">
<label for="totp">Código de verificación (app autenticadora)</label>
<input id="totp" name="totp" type="text" required inputmode="numeric" pattern="[0-9]{6}" maxlength="6">
<button type="submit">Entrar</button>
</form><p class="alt"><a href="solicitar.html">Solicitar acceso</a></p></div>""")


def _solicitar() -> str:
    return _shell("Solicitar acceso", f"""<div class="card"><form method="post" action="/auth/solicitar">
<input type="hidden" name="csrf_token" value="">
<label for="nombre">Nombre completo</label>
<input id="nombre" name="nombre" type="text" required>
<label for="email">Correo</label>
<input id="email" name="email" type="email" required>
<label for="institucion">Institución</label>
<input id="institucion" name="institucion" type="text" required>
<label for="tipo">Tipo de acceso</label>
<select id="tipo" name="tipo" required><option value="interno">ColMayor interno</option>
<option value="invitado">Invitado</option></select>
<label for="motivo">Motivo</label>
<textarea id="motivo" name="motivo" rows="3" required></textarea>
<button type="submit">Enviar solicitud</button>
</form><p class="bul">Las solicitudes las aprueba el administrador ({APPROVAL_MAIL}).</p></div>""")


def _pendiente() -> str:
    return _shell("Solicitud en revisión", f"""<div class="card">
<p class="bul">Tu solicitud está <strong>pendiente de aprobación</strong>. Sin aprobación no se puede entrar.</p>
<p>El administrador (<a href="mailto:{APPROVAL_MAIL}">{APPROVAL_MAIL}</a>) revisará tu solicitud y te avisará por correo.</p>
<p class="alt"><a href="login.html">Volver a entrar</a></p></div>""")


def _activar() -> str:
    return _shell("Activar verificación", """<div class="card"><form method="post" action="/auth/activar-mfa">
<input type="hidden" name="csrf_token" value="">
<p class="bul">Escaneá el código QR con tu app autenticadora y guardá tus códigos de respaldo.</p>
<label for="totp">Código de verificación (6 dígitos)</label>
<input id="totp" name="totp" type="text" required inputmode="numeric" pattern="[0-9]{6}" maxlength="6">
<button type="submit">Activar</button>
</form></div>""")


def run(out_dir: str = "") -> str:
    out = Path(out_dir) if out_dir else OUT_DEFAULT
    out.mkdir(parents=True, exist_ok=True)
    pages = {"login.html": _login(), "solicitar.html": _solicitar(),
             "pendiente.html": _pendiente(), "activar-mfa.html": _activar()}
    for name, html in pages.items():
        assert "<script" not in html.lower(), "HTML puro no debe incluir <script>"
        (out / name).write_text(html, encoding="utf-8")
    print(f"[login] {out} ({len(pages)} páginas)")
    return str(out)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "")
