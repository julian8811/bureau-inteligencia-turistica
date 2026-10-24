# -*- coding: utf-8 -*-
"""Sirve el tablero, expone los agregados y corre la actualización una vez al día.

Si una fuente falla, el JSON anterior permanece y el error queda en el manifiesto.
"""
import threading
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import preparar_fuentes as p
import series_paises

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "open"
CANDADO = threading.Lock()
DIA = 24 * 60 * 60


class Tablero(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        if self.path.startswith("/data/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/estado":
            self.estado()
            return
        super().do_GET()

    def estado(self):
        path = OUT / "manifiesto.json"
        cuerpo = path.read_bytes() if path.exists() else b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, fmt, *args):
        if str(args[0]).startswith("GET /api/") or " 404 " in str(args):
            super().log_message(fmt, *args)


def actualizar():
    if not CANDADO.acquire(blocking=False):
        print("actualizacion en curso")
        return
    try:
        series_paises.ERRORES.clear()
        for nombre, fn in (
            ("paises", series_paises.paises),
            ("wikipedia", series_paises.wiki),
            ("ema", series_paises.ocupacion),
            ("evi", series_paises.evi),
            ("gdelt", series_paises.gdelt),
        ):
            try:
                print("corre", nombre)
                fn()
            except Exception as exc:
                series_paises.fallo(nombre, exc)
                print(traceback.format_exc(limit=2))
        series_paises.manifiesto()
    finally:
        CANDADO.release()


def diario():
    timer = threading.Timer(DIA, diario)
    timer.daemon = True
    timer.start()
    print("corrida diaria")
    actualizar()


def main():
    timer = threading.Timer(DIA, diario)
    timer.daemon = True
    timer.start()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Tablero)
    print("tablero en http://127.0.0.1:8765/")
    server.serve_forever()


if __name__ == "__main__":
    main()
