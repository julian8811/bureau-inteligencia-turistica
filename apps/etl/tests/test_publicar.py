"""Publicación autónoma: export -> bit repo -> tableros. TDD: RED primero."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FILES = ["paises_2025_2026.json", "marca_llm_2025_2026.json", "informe_llm.json", "manifiesto_bureau.json"]


def test_copia_solo_piezas(tmp_path, monkeypatch):
    from export import publicar
    for k in ("GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    src = tmp_path / "src"
    (src / "tableros_bureau").mkdir(parents=True)
    for f in FILES + ["basura.txt"]:
        (src / "tableros_bureau" / f).write_text("{}")
    dest = tmp_path / "dst" / "etl-bureau" / "export" / "tableros_bureau"
    out = publicar.copiar_piezas(src / "tableros_bureau", dest)
    assert sorted(p.name for p in out) == sorted(FILES)
    assert not (dest / "basura.txt").exists()


def test_git_falla_es_skip(monkeypatch, tmp_path):
    from export import publicar
    def boom(*a, **k):
        raise RuntimeError("sin red")
    monkeypatch.setattr(publicar, "_run", boom)
    assert publicar.push_export(str(tmp_path))["status"] == "skip"
    assert publicar.actualizar_tableros(str(tmp_path))["status"] == "skip"


def test_pdfs_skip_sin_playwright(monkeypatch):
    from report import publicar_pdfs
    monkeypatch.setattr(publicar_pdfs, "_build", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    assert publicar_pdfs.run()["status"] == "skip"
