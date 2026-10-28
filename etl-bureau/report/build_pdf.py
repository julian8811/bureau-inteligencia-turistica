"""Genera el Boletín PDF desde el warehouse: sirve web/ por http y lo imprime con Playwright.
Uso: python3 etl-bureau/report/build_pdf.py [--port 8090]
Salida: etl-bureau/informes/boletin_YYYY-MM-DD.pdf
"""
import sys
import threading
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
WEB = BASE / "web"
OUT = BASE / "informes"


def serve(port: int):
    handler = partial(SimpleHTTPRequestHandler, directory=str(WEB))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def build(port: int = 8090) -> Path:
    import requests

    try:
        requests.get(f"http://127.0.0.1:{port}/informe.html", timeout=3)
    except Exception:
        serve(port)
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"boletin_{date.today().isoformat()}.pdf"
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        pg.goto(f"http://127.0.0.1:{port}/informe.html")
        pg.wait_for_function("window.__REPORT_READY__ === true", timeout=90000)
        pg.wait_for_timeout(2500)  # deja asentar ECharts antes de imprimir
        pg.pdf(path=str(dest), format="A4", print_background=True,
               margin={"top": "12mm", "bottom": "14mm", "left": "10mm", "right": "10mm"})
        print("JS errors:", errs if errs else "ninguno")
        b.close()
    print(f"[report] PDF -> {dest} ({dest.stat().st_size // 1024} KB)")
    return dest


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8090
    build(port)
