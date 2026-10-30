"""Construye los PDFs del informe dentro del daily. Nunca levanta excepción."""
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def _build(port: int, html: str, pano: bool = False):
    from . import build_pdf
    return build_pdf.build(port, html, pano)


def run() -> dict:
    hechos = []
    for html, pano in (("informe-llm.html", False), ("informe-16x9.html", True)):
        try:
            dest = _build(8090, html, pano)
            hechos.append(Path(dest).name)
        except Exception as e:
            print(f"[pdfs][SKIP] {html} ({e})")
            return {"status": "skip", "hechos": hechos}
    return {"status": "ok", "hechos": hechos}


if __name__ == "__main__":
    print(run())
