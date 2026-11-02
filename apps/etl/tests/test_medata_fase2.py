"""MEData fase 2 (T4 S1-S3): mas zonas/categorias desde el baseline + SKIP honesto.

Portal re-verificado 2026-11-01: series congeladas en oct-2023, sin datasets
nuevos sin key (CKAN apagado, solo CSVs Drupal directos). Cobertura extra via
derivados locales en extract/medata.py. TDD: RED primero.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import medata  # noqa: E402
from transform import kpis  # noqa: E402


# --- PITS mensual: parse fixture ---

def test_pits_mensual_parse_fixture():
    df = pd.DataFrame([
        {"pit_nacionalidad": "Extranjero", "pit_nombre": "PI_COMUNA_13",
         "pit_periodo": 202209, "pit_totalvisitas": 218},
        {"pit_nacionalidad": "Colombiano", "pit_nombre": "PI_COMUNA_13",
         "pit_periodo": 202209, "pit_totalvisitas": 100},
        {"pit_nacionalidad": "Extranjero", "pit_nombre": "PIT_PARQUE_ARVI",
         "pit_periodo": 202209, "pit_totalvisitas": -1},
    ])
    out = medata.build_pits_mensual(df)
    assert len(out) == 1
    assert out["pit_periodo"].iloc[0] == 202209
    assert out["visitas_total"].iloc[0] == 318  # -1 (sin dato) cuenta como 0
    assert out["puntos_activos"].iloc[0] == 1  # solo PI_COMUNA_13 con >0


def test_pits_mensual_vacio():
    out = medata.build_pits_mensual(pd.DataFrame())
    assert out.empty


# --- Zonas ranking: parse fixture ---

def test_zonas_ranking_parse_fixture():
    df = pd.DataFrame([
        {"ocu_periodo": 202209, "ocu_valor": 79.3, "ocu_zona": "LAURELES"},
        {"ocu_periodo": 202208, "ocu_valor": 80.0, "ocu_zona": "LAURELES"},
        {"ocu_periodo": 202209, "ocu_valor": 49.9, "ocu_zona": "CENTRO"},
    ])
    out = medata.build_zonas_ranking(df)
    assert set(out["ocu_zona"]) == {"LAURELES", "CENTRO"}
    assert out.sort_values("ocu_prom", ascending=False)["ocu_zona"].iloc[0] == "LAURELES"


def test_zonas_ranking_vacio():
    out = medata.build_zonas_ranking(pd.DataFrame())
    assert out.empty


# --- Eventos uplift: parse fixture ---

def test_eventos_uplift_parse_fixture():
    base = pd.DataFrame([
        {"ocu_periodo": 202209, "ocu_valor": 60.0, "ocu_zona": "POBLADO"},
        {"ocu_periodo": 202209, "ocu_valor": 50.0, "ocu_zona": "CENTRO"},
    ])
    feria = pd.DataFrame([
        {"ocu_periodo": 202209, "ocu_valor": 70.0, "ocu_zona": "POBLADO"},
        {"ocu_periodo": 202209, "ocu_valor": 65.0, "ocu_zona": "CENTRO"},
    ])
    out = medata.build_eventos_uplift({"feria": feria, "base": base})
    assert len(out) == 1
    assert out["evento"].iloc[0] == "feria"
    # feria prom 67.5 vs base prom 55.0 -> uplift 12.5pp
    assert out["uplift_pp"].iloc[0] == 12.5


def test_eventos_uplift_sin_base():
    out = medata.build_eventos_uplift({})
    assert out.empty


# --- run nunca levanta ---

def test_medata_run_nunca_levanta(monkeypatch):
    def boom(url):
        raise ConnectionError("sin red")

    monkeypatch.setattr(medata, "fetch", boom)
    outs = medata.run()  # no debe levantar
    assert isinstance(outs, list)
    assert len(outs) >= len(medata.FILES)


# --- KPIs extra: ceros sin CSV ---

def test_kpis_medata_extra_ceros_sin_csv(monkeypatch):
    monkeypatch.setattr(kpis, "latest_raw", lambda name: pd.DataFrame())
    out = kpis.kpis_medata_extra()
    assert out["pits_mensual_ult"] == 0
    assert out["pits_mensual_periodo"] == ""
    assert out["zonas_top"] == ""
    assert out["zonas_n"] == 0
    assert out["eventos_uplift_max_tag"] == ""
    assert out["eventos_uplift_max_pp"] == 0.0


# --- KPIs extra: con fixture ---

def test_kpis_medata_extra_con_fixture(monkeypatch):
    pits = pd.DataFrame([
        {"pit_periodo": 202209, "visitas_total": 318, "puntos_activos": 1},
        {"pit_periodo": 202208, "visitas_total": 200, "puntos_activos": 1},
    ])
    zonas = pd.DataFrame([
        {"ocu_zona": "LAURELES", "ocu_prom": 79.6, "n_meses": 2},
        {"ocu_zona": "CENTRO", "ocu_prom": 49.9, "n_meses": 1},
    ])
    uplift = pd.DataFrame([
        {"evento": "feria", "occ_evento": 67.5, "occ_base": 55.0, "uplift_pp": 12.5},
        {"evento": "moda", "occ_evento": 58.0, "occ_base": 55.0, "uplift_pp": 3.0},
    ])

    def fake_latest(name):
        return {"medata_pits_mensual": pits,
                "medata_ocupacion_zonas": zonas,
                "medata_eventos_uplift": uplift}.get(name, pd.DataFrame())

    monkeypatch.setattr(kpis, "latest_raw", fake_latest)
    out = kpis.kpis_medata_extra()
    assert out["pits_mensual_ult"] == 318
    assert out["pits_mensual_periodo"] == "202209"
    assert out["zonas_top"] == "LAURELES"
    assert out["zonas_n"] == 2
    assert out["eventos_uplift_max_tag"] == "feria"
    assert out["eventos_uplift_max_pp"] == 12.5


# --- PRESERVE: kpis_medata baseline intacto ---

def test_kpis_medata_baseline_intacto(monkeypatch):
    occ = pd.DataFrame([
        {"ocu_indicador": "OCUPA_HOTELERA", "ocu_periodo": 202309, "ocu_valor": 71.7},
        {"ocu_periodo": 202310, "ocu_indicador": "OCUPA_HOTELERA", "ocu_valor": 67.1},
    ])
    monkeypatch.setattr(kpis, "latest_raw",
                        lambda name: occ if name == "medata_ocupacion_med" else pd.DataFrame())
    out = kpis.kpis_medata()
    assert out["occ_med_ult"] == 67.1
    assert out["occ_med_periodo"] == "202310"
