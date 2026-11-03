"""Regresiones del plan de fuentes: el daily importa y los parsers no inventan filas."""
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_daily_importa():
    from orchestration import daily
    nombres = [step.__name__ for step in ()]
    assert hasattr(daily, "main")
    assert callable(daily.trm_co.run)
    assert callable(daily.avisos_viaje.run)
    assert callable(daily.bureau_runner.run)
    assert nombres == []


def test_trm_oficial_ordena_y_descarta_vacios():
    from extract.trm_co import rows_from_socrata
    df = rows_from_socrata([
        {"valor": "3182.99", "vigenciadesde": "2026-10-31T00:00:00.000"},
        {"valor": "", "vigenciadesde": "2026-10-30T00:00:00.000"},
        {"valor": "3166.91", "vigenciadesde": "2026-10-30T00:00:00.000"},
    ])
    assert list(df["date"]) == ["2026-10-30", "2026-10-31"]
    assert df["rate_cop"].iloc[-1] == "3182.99"


def test_aviso_us_solo_colombia():
    from extract.avisos_viaje import fila_us
    assert fila_us({"Category": ["IR"], "Title": "Iran"}) is None
    fila = fila_us({"Category": ["CO"], "Title": "Colombia - Level 3", "Updated": "2026-03-30", "Summary": "<b>Reconsider</b>"})
    assert fila["pais"] == "Estados Unidos"
    assert "Reconsider" in fila["resumen"]
    assert "<" not in fila["resumen"]


def test_gdelt_cuenta_medellin_en_el_zip():
    from extract.gdelt_marca import count_medellin
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("x.gkg.csv", "Bogota turismo\nMedellín hotel\nmedellin flores\n")
    assert count_medellin(buf.getvalue()) == 2


def test_bts_filtra_colombia():
    from extract.bts_colombia import filas
    df = filas([
        {"country": "AE", "year": "2024", "inbound_international_seats": "1"},
        {"country": "CO", "year": "2026", "date": "2026-06-01T00:00:00.000",
         "inbound_international": "10", "inbound_international_1": "20",
         "inbound_international_seats": "30", "outbound_international": "11",
         "outbound_international_1": "21", "outbound_international_seats": "31"},
    ])
    assert list(df["mes"]) == ["06"]
    assert int(df["llegadas_sillas"].iloc[0]) == 30


def test_runner_no_pisa_un_json_ok(tmp_path, monkeypatch):
    from export import bureau_runner
    out = tmp_path / "pieza.json"
    out.write_text('{"estado": "ok", "serie": [1]}', encoding="utf-8")

    class Mod:
        __name__ = "falso"
        OUT = out

        @staticmethod
        def main():
            out.write_text('{"estado": "skip", "motivo": "vacio"}', encoding="utf-8")

    bureau_runner._correr(Mod)
    assert '"ok"' in out.read_text(encoding="utf-8")
