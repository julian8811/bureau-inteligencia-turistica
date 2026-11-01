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


def build(port: int = 8090, html: str = "informe.html", pano: bool = False) -> Path:
    import requests

    try:
        requests.get(f"http://127.0.0.1:{port}/{html}", timeout=3)
    except Exception:
        serve(port)
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    stem = Path(html).stem
    dest = OUT / f"{stem}_{date.today().isoformat()}.pdf"
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        pg.goto(f"http://127.0.0.1:{port}/{html}")
        pg.wait_for_function("window.__REPORT_READY__ === true", timeout=90000)
        pg.wait_for_timeout(2500)  # deja asentar ECharts antes de imprimir
        args: dict = {"path": str(dest), "print_background": True}
        if pano:
            args.update({"width": "13.33in", "height": "7.5in",
                         "margin": {"top": "0", "bottom": "0", "left": "0", "right": "0"},
                         "display_header_footer": False, "prefer_css_page_size": False})
        else:
            args.update({"format": "A4",
                         "margin": {"top": "12mm", "bottom": "16mm", "left": "10mm", "right": "10mm"},
                         "display_header_footer": True,
                         "header_template": "<span></span>",
                         "footer_template": ('<div style="width:100%;font-size:8pt;color:#5A6C7D;'
                                              'padding:0 12mm;text-align:right;">pág. <span class="pageNumber"></span>'
                                              ' / <span class="totalPages"></span></div>')})
        pg.pdf(**args)
        print("JS errors:", errs if errs else "ninguno")
        b.close()
    print(f"[report] PDF -> {dest} ({dest.stat().st_size // 1024} KB)")
    return dest


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8090
    html = sys.argv[sys.argv.index("--html") + 1] if "--html" in sys.argv else "informe.html"
    pano = "--pano" in sys.argv or Path(html).stem.endswith("16x9")
    build(port, html, pano)
