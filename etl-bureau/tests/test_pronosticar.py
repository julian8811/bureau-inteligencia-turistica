"""El pronóstico publica el modelo que gana el ensayo, no el más complejo."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import pronosticar as pr


def test_repara_el_glitch_y_respeta_un_bache():
    out, idxs = pr.reparar([100, 100, 1, 100, 100])
    assert out[2] == 100
    assert idxs == [2]
    out2, idxs2 = pr.reparar([100, 80, 70, 80, 100])
    assert idxs2 == []
    assert out2[2] == 70


def test_ceros_iniciales_no_entran():
    periodos, valores, caidos = pr.caer_ceros_iniciales(
        ["2018-07", "2018-08", "2018-09", "2018-10"],
        [0, 0, 0, 25],
    )
    assert caidos == ["2018-07", "2018-08", "2018-09"]
    assert valores == [25]
    assert periodos == ["2018-10"]


def test_empate_del_dos_porciento_prefiere_el_simple():
    assert pr.elegir({"gradiente": 9.9, "holt_winters": 10.1, "estacional": 10.0}) == "estacional"
    assert pr.elegir({"gradiente": 8.0, "holt_winters": 9.9, "estacional": 10.0}) == "gradiente"
    assert pr.elegir({"estacional": 0.0, "holt_winters": 0.01}) == "estacional"


def test_estacional_repite_el_mismo_mes():
    assert pr.pronostico_estacional(list(range(1, 14)), 3) == [2, 3, 4]


def test_serie_que_se_repite_elige_el_mes_anterior():
    periodos, valores = [], []
    for anio in range(2022, 2026):
        for mes in range(1, 13):
            periodos.append(f"{anio}-{mes:02d}")
            valores.append(100 + mes)
    spec = {
        "id": "sintetica",
        "tab": "mercados",
        "nombre": "Sintética",
        "unidad": "pasajeros",
        "decimales": 0,
        "piso": 0,
        "techo": None,
        "caer_ceros": False,
        "notas": [],
    }
    fila = pr.construir_serie(spec, periodos, valores, {"holt_winters": True, "gradiente": True})
    assert fila["modelo"] == "estacional"
    assert fila["supera_estacional"] is False
    assert [p["valor"] for p in fila["pronostico"]] == [101, 102, 103, 104, 105, 106]
    assert fila["pronostico"][0]["periodo"] == "2026-01"
    assert fila["mae"] == 0


def test_la_ocupacion_no_pasa_de_100():
    assert pr.recortar(140, 0, 100) == 100
    assert pr.recortar(-3, 0, None) == 0


def test_run_no_borra_el_json_si_faltan_insumos(tmp_path, monkeypatch):
    destino = tmp_path / "pronosticos.json"
    destino.write_text('{"id":"viejo"}\n', encoding="utf-8")
    monkeypatch.setattr(pr, "OUT", destino)
    monkeypatch.setattr(pr, "leer_vivo", lambda: None)
    monkeypatch.setattr(pr, "leer_slim", lambda path=None: (_ for _ in ()).throw(FileNotFoundError("sin insumo")))
    assert pr.run()["status"] == "skip"
    assert json.loads(destino.read_text(encoding="utf-8"))["id"] == "viejo"


def test_daily_entrena_antes_de_publicar():
    from orchestration import daily
    texto = Path(daily.__file__).read_text(encoding="utf-8")
    assert texto.index("bureau_runner.run") < texto.index("pronosticar.run")
    assert texto.index("pronosticar.run") < texto.index("publicar_tableros.push_export")
    from export import publicar
    assert "pronosticos.json" in publicar.PIEZAS


def test_el_corte_publicado_declara_ganador_y_banda():
    doc = json.loads(pr.OUT.read_text(encoding="utf-8"))
    assert doc["id"] == "bureau-pronostico"
    assert doc["resumen"]["n"] == 10
    por_id = {s["id"]: s for s in doc["series"]}
    assert por_id["llegadas_brasil"]["reparados"] == ["2022-05"]
    assert por_id["llegadas_brasil"]["modelo"] == "gradiente"
    assert por_id["llegadas_mexico"]["modelo"] == "estacional"
    assert por_id["llegadas_mexico"]["empate_simple"] is True
    assert por_id["llegadas_estados_unidos"]["modelo"] == "estacional"
    assert por_id["llegadas_estados_unidos"]["empate_simple"] is False
    assert por_id["homicidios"]["n_observado"] == 96
    assert por_id["homicidios"]["corte"] == "2026-09"
    assert "amplia" in " ".join(por_id["homicidios"]["notas"])
    for serie in doc["series"]:
        assert len(serie["pronostico"]) == 6
        assert any(c["modelo"] == "estacional" for c in serie["comparacion"])
        for punto in serie["pronostico"]:
            assert punto["bajo"] <= punto["valor"] <= punto["alto"]
    assert "red neuronal" in doc["fuera"]


def test_el_mes_del_gradiente_es_el_calendario():
    assert pr._mes_siguiente(6, 1) == 7
    assert pr._mes_siguiente(12, 1) == 1
    assert pr._mes_siguiente(6, 6) == 12
