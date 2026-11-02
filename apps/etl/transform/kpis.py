"""Transform: raw diario -> modelo estrella + KPIs del Plan Dashboard (pestaña Excel).
Tablas: fact_demanda, fact_mice, fact_marca, dim_fecha, dim_mercado.
Fórmulas espejo del Excel: win_rate=ganados/recibidos, derrama=asist*gasto*estadía,
revpar=occ*adr, sentimiento=(pos-neg)/total, engagement=inter/alcance.
"""
from datetime import date
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

def latest_raw(name: str) -> pd.DataFrame:
    cands = sorted(RAW.glob(f"*/{name}.csv"))
    if not cands:
        return pd.DataFrame()
    try:
        return pd.read_csv(cands[-1])
    except Exception as e:
        print(f"[transform][WARN] {name}: no se pudo leer ({e}) -> vacío")
        return pd.DataFrame()

def kpis_marca(alerts: pd.DataFrame) -> dict:
    if alerts.empty:
        return {"menciones": 0, "sentimiento_neto": 0.0, "share_medellin": 0.0}
    t = alerts["titulo"].str.lower().fillna("")
    pos = t.str.contains("récord|premio|líder|crece|top|galardón|inaugura").sum()
    neg = t.str.contains("insegur|homicidio|estafa|cancel|crisis|colapso|denuncia").sum()
    total = max(len(alerts), 1)
    med = t.str.contains("medell").sum()
    return {
        "menciones": int(len(alerts)),
        "sentimiento_neto": round((pos - neg) / total, 3),  # =(Pos-Neg)/Total
        "share_medellin": round(med / total, 3),
    }

def kpis_demanda() -> dict:
    """Demanda desde Socrata cableado: Medellín no-residentes + aéreo MDE/EOH."""
    med = latest_raw("medellin_no_residentes")
    aer = latest_raw("aereo_mde_eoh")
    out: dict = {}
    try:
        if not med.empty and "cant_extranjeros_no_residentes" in med.columns:
            med["cant_extranjeros_no_residentes"] = pd.to_numeric(med["cant_extranjeros_no_residentes"], errors="coerce").fillna(0)
            out["llegadas_medellin_nr"] = int(med["cant_extranjeros_no_residentes"].sum())
            if "paisoeeresidencia" in med.columns:
                top = med.groupby("paisoeeresidencia")["cant_extranjeros_no_residentes"].sum().sort_values(ascending=False).head(5)
                out["top1_emisor"] = str(top.index[0]) if len(top) else ""
                out["share_top5"] = round(top.sum() / max(med["cant_extranjeros_no_residentes"].sum(), 1), 3)
        if not aer.empty and "pasajeros" in aer.columns:
            aer["pasajeros"] = pd.to_numeric(aer["pasajeros"], errors="coerce").fillna(0)
            lleg = aer[aer.get("sentido", "") == "llegada"]["pasajeros"].sum() if "sentido" in aer.columns else 0
            sal = aer[aer.get("sentido", "") == "salida"]["pasajeros"].sum() if "sentido" in aer.columns else 0
            out["pax_llegadas_mde"] = int(lleg)
            out["pax_salidas_mde"] = int(sal)
    except Exception as e:
        print(f"[transform][WARN] kpis_demanda: {e}")
    return out

def kpis_dane() -> dict:
    egit = latest_raw("dane_egit_gasto_dia")
    enh = latest_raw("dane_enh")
    out = {"dane_egit_ok": int(not egit.empty), "dane_enh_ok": int(not enh.empty),
           "dane_egit_filas": int(len(egit)), "dane_enh_filas": int(len(enh))}
    try:
        # Gasto promedio día último trimestre disponible (serie nacional 24 ciudades, proxy gasto)
        if not egit.empty and {"trimestre", "valor"} <= set(egit.columns):
            last = egit["trimestre"].dropna().unique().tolist()[-1]
            sub = egit[egit["trimestre"] == last]
            total = sub[sub["concepto"].astype(str).str.contains("Total|total", na=False)]["valor"]
            if not total.empty:
                out["gasto_prom_dia_cop"] = float(pd.to_numeric(total, errors="coerce").dropna().iloc[0])
                out["gasto_trimestre"] = str(last)
    except Exception as e:
        print(f"[transform][WARN] kpis_dane gasto: {e}")
    return out

def kpis_gdelt() -> dict:
    g = latest_raw("gdelt_marca")
    if g.empty:
        return {"gdelt_vol_7d": 0}
    vol = pd.to_numeric(g.get("value", 0), errors="coerce").fillna(0).sum() if "value" in g.columns else len(g)
    return {"gdelt_vol_7d": int(vol), "gdelt_queries": int(g["query"].nunique()) if "query" in g.columns else 0}

def kpis_medata() -> dict:
    """MEData histórico (series congeladas 2023): ocupación, tarifa, PITS, llegadas MDE por país."""
    out: dict = {}
    try:
        occ = latest_raw("medata_ocupacion_med")
        if not occ.empty:
            per = [c for c in occ.columns if "periodo" in c.lower()][0]
            val = [c for c in occ.columns if "valor" in c.lower()][0]
            occ = occ.sort_values(per)
            out["occ_med_ult"] = float(occ[val].iloc[-1])
            out["occ_med_periodo"] = str(occ[per].iloc[-1])
            out["occ_med_max12"] = float(occ[val].tail(12).max())
        tar = latest_raw("medata_tarifa_med")
        if not tar.empty:
            per = [c for c in tar.columns if "periodo" in c.lower()][0]
            val = [c for c in tar.columns if "valor" in c.lower()][0]
            tar = tar.sort_values(per)
            out["tarifa_med_ult"] = float(tar[val].iloc[-1])
            out["tarifa_med_periodo"] = str(tar[per].iloc[-1])
        pits = latest_raw("medata_pits")
        if not pits.empty:
            out["pits_filas"] = int(len(pits))
        ext = latest_raw("medata_extranjeros_pais_mde")
        if not ext.empty:
            per = [c for c in ext.columns if "periodo" in c.lower()][0]
            last = str(ext[per].max())
            sub = ext[ext[per].astype(str) == last]
            val = [c for c in sub.columns if "valor" in c.lower()][0]
            pais = [c for c in sub.columns if "origen" in c.lower() or "pais" in c.lower()][0]
            top = sub.groupby(pais)[val].sum().sort_values(ascending=False)
            out["mde_top_emisor_hist"] = str(top.index[0]) if len(top) else ""
            out["mde_top3_share_hist"] = round(top.head(3).sum() / max(top.sum(), 1), 3)
            out["mde_hist_periodo"] = last
    except Exception as e:
        print(f"[transform][WARN] kpis_medata: {e}")
    return out


MEDATA_EXTRA_ZEROS = {
    "pits_mensual_ult": 0, "pits_mensual_periodo": "", "pits_puntos_activos": 0,
    "zonas_top": "", "zonas_n": 0,
    "eventos_uplift_max_tag": "", "eventos_uplift_max_pp": 0.0,
}


def kpis_medata_extra() -> dict:  # type: ignore[no-untyped-def]
    """T4 (S1-S3): derivados fase 2 (PITS mensual, ranking zonas, uplift eventos).
    Sin CSV -> ceros (SKIP honesto), nunca levanta."""
    try:
        pits = latest_raw("medata_pits_mensual")
        zonas = latest_raw("medata_ocupacion_zonas")
        uplift = latest_raw("medata_eventos_uplift")
        if pits.empty and zonas.empty and uplift.empty:  # type: ignore[attr-defined]
            print("[transform][SKIP] medata_extra: sin CSVs -> 0")
            return dict(MEDATA_EXTRA_ZEROS)
        out: dict = dict(MEDATA_EXTRA_ZEROS)
    except Exception as e:
        print(f"[transform][SKIP] medata_extra: {e}")
        return dict(MEDATA_EXTRA_ZEROS)
    try:  # PITS: ultimo periodo
        if not pits.empty and {"pit_periodo", "visitas_total"} <= set(pits.columns):  # type: ignore[attr-defined]
            p = pits.copy()  # type: ignore[assignment]
            p["pit_periodo"] = p["pit_periodo"].astype(str)  # type: ignore[attr-defined]
            last = str(p["pit_periodo"].max())  # type: ignore[attr-defined]
            sub = p[p["pit_periodo"] == last]  # type: ignore[assignment,attr-defined]
            out["pits_mensual_ult"] = int(pd.to_numeric(sub["visitas_total"], errors="coerce").fillna(0).sum())  # type: ignore[call-overload,attr-defined]
            out["pits_mensual_periodo"] = last
            if "puntos_activos" in sub.columns:  # type: ignore[attr-defined]
                out["pits_puntos_activos"] = int(pd.to_numeric(sub["puntos_activos"], errors="coerce").fillna(0).sum())  # type: ignore[call-overload,attr-defined]
    except Exception as e:
        print(f"[transform][SKIP] medata_extra pits: {e}")
    try:  # Zonas: top promedio
        if not zonas.empty and {"ocu_zona", "ocu_prom"} <= set(zonas.columns):  # type: ignore[attr-defined]
            z = zonas.copy()  # type: ignore[assignment]
            z["ocu_prom"] = pd.to_numeric(z["ocu_prom"], errors="coerce")  # type: ignore[call-overload]
            z = z.dropna(subset=["ocu_prom"])  # type: ignore[assignment]
            if not z.empty:  # type: ignore[attr-defined]
                top = z.sort_values("ocu_prom", ascending=False).iloc[0]  # type: ignore[attr-defined]
                out["zonas_top"] = str(top["ocu_zona"])
                out["zonas_n"] = int(len(z))  # type: ignore[arg-type]
    except Exception as e:
        print(f"[transform][SKIP] medata_extra zonas: {e}")
    try:  # Uplift: max pp
        if not uplift.empty and {"evento", "uplift_pp"} <= set(uplift.columns):  # type: ignore[attr-defined]
            u = uplift.copy()  # type: ignore[assignment]
            u["_pp"] = pd.to_numeric(u["uplift_pp"], errors="coerce")  # type: ignore[call-overload]
            u = u.dropna(subset=["_pp"])  # type: ignore[assignment]
            if not u.empty:  # type: ignore[attr-defined]
                best = u.sort_values("_pp", ascending=False).iloc[0]  # type: ignore[attr-defined]
                out["eventos_uplift_max_tag"] = str(best["evento"])
                out["eventos_uplift_max_pp"] = round(float(best["_pp"]), 2)
    except Exception as e:
        print(f"[transform][SKIP] medata_extra uplift: {e}")
    return out

# Normalización de países entre fuentes (Migración usa gentilicios/variantes distintas; case-insensitive porque 2026 viene en Title Case distinto)
PAIS_ALIAS = {
    "estados unidos de america": "Estados Unidos",
    "estados unidos": "Estados Unidos",
    "venezuela (republica bolivariana de)": "Venezuela",
    "venezuela": "Venezuela",
    "republica dominicana": "Rep. Dominicana",
    "corea del sur": "Corea",
    "rusia (federacion rusa)": "Rusia",
    "rusia": "Rusia",
    "iran (republica islamica de)": "Irán",
    "iran": "Irán",
    "tanzania (republica unida de)": "Tanzania",
    "moldavia (republica de)": "Moldavia",
    "macedonia del norte": "Macedonia",
    "macedonia": "Macedonia",
    "mexico": "México",
    "panama": "Panamá",
    "peru": "Perú",
    "canada": "Canadá",
    "espana": "España",
    "brasil": "Brasil",
    "chile": "Chile",
    "ecuador": "Ecuador",
    "costa rica": "Costa Rica",
    "argentina": "Argentina",
    "reino unido": "Reino Unido",
    "francia": "Francia",
    "alemania": "Alemania",
    "paises bajos": "Países Bajos",
    "holanda": "Países Bajos",
    "italia": "Italia",
    "portugal": "Portugal",
    "suiza": "Suiza",
    "belgica": "Bélgica",
    "austria": "Austria",
    "suecia": "Suecia",
    "noruega": "Noruega",
    "dinamarca": "Dinamarca",
    "polonia": "Polonia",
    "el salvador": "El Salvador",
    "guatemala": "Guatemala",
    "honduras": "Honduras",
    "cuba": "Cuba",
    "puerto rico": "Puerto Rico",
    "jamaica": "Jamaica",
    "china": "China",
    "japon": "Japón",
    "india": "India",
    "australia": "Australia",
    "colombia": "Colombia",
}
TRENDS_GEO_PAIS = {"US": "Estados Unidos", "ES": "España", "MX": "México", "PA": "Panamá", "PE": "Perú"}

def norm_pais(s: str) -> str:
    import unicodedata
    s = str(s).strip()
    key = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()
    return PAIS_ALIAS.get(key, s)

def kpis_pais() -> pd.DataFrame:
    """Tabla por país: llegadas Medellín + Colombia, pax MDE, salidas, intención Trends, YoY y share."""
    try:
        med = latest_raw("medellin_no_residentes")
        nac = latest_raw("entradas_nacionalidad")
        aer = latest_raw("aereo_mde_eoh")
        sal = latest_raw("salidas_destino")
        frames = {}
        if not med.empty:
            med["pais"] = med["paisoeeresidencia"].map(norm_pais)
            med["cant_extranjeros_no_residentes"] = pd.to_numeric(med["cant_extranjeros_no_residentes"], errors="coerce").fillna(0)
            med["a_o"] = med["a_o"].astype(str)
            frames["med"] = med.groupby(["pais", "a_o"])["cant_extranjeros_no_residentes"].sum().reset_index()
        if not nac.empty:
            nac["pais"] = nac["nacionalidad"].map(norm_pais)
            nac["total"] = pd.to_numeric(nac["total"], errors="coerce").fillna(0)
            nac["a_o"] = nac["a_o"].astype(str)
            frames["nac"] = nac.groupby(["pais", "a_o"])["total"].sum().reset_index()
        if not aer.empty:
            aer["pasajeros"] = pd.to_numeric(aer["pasajeros"], errors="coerce").fillna(0)
            lleg = aer[aer.get("sentido", "") == "llegada"].copy()
            lleg["pais"] = lleg.get("pais_origen", "").map(norm_pais)
            lleg["a_o"] = lleg["a_o"].astype(str)
            frames["aer"] = lleg.groupby(["pais", "a_o"])["pasajeros"].sum().reset_index()
        if not sal.empty:
            sal["pais"] = sal["pa_s_destino"].map(norm_pais)
            sal["total"] = pd.to_numeric(sal["total"], errors="coerce").fillna(0)
            sal["a_o"] = sal["a_o"].astype(str)
            frames["sal"] = sal.groupby(["pais", "a_o"])["total"].sum().reset_index()
        if not frames:
            return pd.DataFrame()
        years = sorted({y for f in frames.values() for y in f["a_o"].unique().tolist()})
        # El año en curso viene parcial (2026 trae ene-jun) -> YoY sobre los dos últimos COMPLETOS
        ytd = years[-1]
        y1 = years[-2] if len(years) > 1 else years[-1]
        y0 = years[-3] if len(years) > 2 else y1
        paises = sorted({p for f in frames.values() for p in f["pais"].unique().tolist()})
        rows = []
        for p in paises:
            r = {"pais": p}
            for key, col in (("med", "cant_extranjeros_no_residentes"), ("nac", "total"), ("aer", "pasajeros"), ("sal", "total")):
                f = frames.get(key)
                v1 = float(f[(f["pais"] == p) & (f["a_o"] == y1)][col].sum()) if f is not None else 0.0
                v0 = float(f[(f["pais"] == p) & (f["a_o"] == y0)][col].sum()) if f is not None else 0.0
                vy = float(f[(f["pais"] == p) & (f["a_o"] == ytd)][col].sum()) if f is not None else 0.0
                r[f"{key}_{y1}"] = v1
                r[f"{key}_yoy"] = round((v1 - v0) / max(v0, 1), 3)
                r[f"{key}_{ytd}_ytd"] = vy
            rows.append(r)
        out = pd.DataFrame(rows)
        tot = out[f"med_{y1}"].sum()
        out["share_med"] = (out[f"med_{y1}"] / max(tot, 1)).round(4)
        out["intencion_trends"] = out["pais"].map({v: k for k, v in TRENDS_GEO_PAIS.items()})
        out = out.sort_values(f"med_{y1}", ascending=False).reset_index(drop=True)
        out["ano_ref"], out["ano_base"], out["ano_ytd"] = y1, y0, ytd
        p = PROC / "pais_dashboard.csv"
        out.to_csv(p, index=False)
        print(f"[transform] pais_dashboard: {len(out)} países ({y0}->{y1}), top={out.iloc[0]['pais'] if len(out) else '—'}")
        return out
    except Exception as e:
        print(f"[transform][WARN] kpis_pais: {e}")
        return pd.DataFrame()

def kpis_destinos(top_n: int = 12) -> pd.DataFrame:
    """Ranking destinos Colombia x año con YoY y share. Fuente: ciudades_llegadas."""
    try:
        df = latest_raw("ciudades_llegadas")
        if df.empty:
            return pd.DataFrame()
        df["llegadas"] = pd.to_numeric(df["llegadas"], errors="coerce").fillna(0)
        df["a_o"] = df["a_o"].astype(str)
        years = sorted(df["a_o"].unique().tolist())
        ytd = years[-1]
        y1 = years[-2] if len(years) > 1 else years[-1]
        y0 = years[-3] if len(years) > 2 else y1
        piv = df.pivot_table(index="ciudad", columns="a_o", values="llegadas", aggfunc="sum").fillna(0)
        out = pd.DataFrame({
            "ciudad": piv.index,
            f"llegadas_{y1}": piv[y1].values if y1 in piv.columns else 0,
            "yoy": ((piv[y1] - piv[y0]) / piv[y0].replace(0, 1)).values if y0 in piv.columns else 0,
            f"llegadas_{ytd}_ytd": piv[ytd].values if ytd in piv.columns else 0,
        })
        out["share"] = (out[f"llegadas_{y1}"] / max(out[f"llegadas_{y1}"].sum(), 1)).round(4)
        out = out.sort_values(f"llegadas_{y1}", ascending=False).head(top_n).reset_index(drop=True)
        out["ano_ref"], out["ano_base"], out["ano_ytd"] = y1, y0, ytd
        p = PROC / "destinos_dashboard.csv"
        out.to_csv(p, index=False)
        print(f"[transform] destinos: {len(out)} ciudades ({y0}->{y1}), top={out.iloc[0]['ciudad'] if len(out) else '—'}")
        return out
    except Exception as e:
        print(f"[transform][WARN] kpis_destinos: {e}")
        return pd.DataFrame()

MES = {"ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3, "abr": 4, "abril": 4,
       "may": 5, "mayo": 5, "jun": 6, "junio": 6, "jul": 7, "julio": 7, "ago": 8, "agosto": 8,
       "sep": 9, "septiembre": 9, "setiembre": 9, "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11,
       "dic": 12, "diciembre": 12}

def trim3(df: pd.DataFrame, val_col: str, mes_col: str) -> tuple[pd.DataFrame, str, str]:
    """Últimos 3 meses disponibles + mismo periodo año anterior. Retorna (df_filtrado, etiqueta, etiqueta_base)."""
    d = df.copy()
    num = pd.to_numeric(d[mes_col].astype(str).str.strip(), errors="coerce")
    if num.notna().mean() > 0.9:
        d["mes_n"] = num.astype(int)
    else:
        d["mes_n"] = d[mes_col].astype(str).str.strip().str.lower().map(MES)
    d["a_o"] = d["a_o"].astype(str)
    d = d.dropna(subset=["mes_n"])
    if d.empty:
        raise ValueError("sin meses parseables")
    d["mes_n"] = d["mes_n"].astype(int)
    max_y, max_m = d["a_o"].max(), int(d[d["a_o"] == d["a_o"].max()]["mes_n"].max())
    # ventana: últimos 3 meses desde el máximo
    win = []
    y, m = int(max_y), max_m
    for _ in range(3):
        win.append((str(y), m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    cur = d[d.apply(lambda r: (r["a_o"], int(r["mes_n"])) in win, axis=1)]
    # base: mismos 3 meses, año anterior
    win_base = [(str(int(a) - 1), mm) for a, mm in win]
    base = d[d.apply(lambda r: (r["a_o"], int(r["mes_n"])) in win_base, axis=1)]
    meses_es = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun", 7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}
    lab = f"{meses_es[win[-1][1]]}-{win[-1][0]} a {meses_es[win[0][1]]}-{win[0][0]}"
    return cur, base, lab

def kpis_ult3m() -> dict:
    """Agregados últimos 3 meses disponibles (hoy: abr-jun 2026) + frescura por fuente."""
    out: dict = {}
    try:
        med = latest_raw("medellin_no_residentes")
        if not med.empty:
            med["pais"] = med["paisoeeresidencia"].map(norm_pais)
            med["cant_extranjeros_no_residentes"] = pd.to_numeric(med["cant_extranjeros_no_residentes"], errors="coerce").fillna(0)
            cur, base, lab = trim3(med, "cant_extranjeros_no_residentes", "mes")
            t = cur.groupby("pais")["cant_extranjeros_no_residentes"].sum().sort_values(ascending=False)
            b = base.groupby("pais")["cant_extranjeros_no_residentes"].sum()
            u = pd.DataFrame({"pais": t.index, "med_ult3m": t.values})
            u["med_ult3m_yoy"] = u.apply(lambda r: round((r["med_ult3m"] - b.get(r["pais"], 0)) / max(b.get(r["pais"], 0), 1), 3), axis=1)
            u["ventana"] = lab
            u.to_csv(PROC / "ult3m_pais.csv", index=False)
            out["med_ult3m_total"] = int(t.sum())
            out["med_ult3m_yoy"] = round((t.sum() - b.sum()) / max(b.sum(), 1), 3)
            out["med_ventana"] = lab
        for key, col_m, col_v in (("entradas_nacionalidad", None, "total"), ("aereo_mde_eoh", "n_mero_de_mes", "pasajeros"), ("salidas_destino", None, "total")):
            df = latest_raw(key)
            if df.empty:
                continue
            mc = col_m or ("mes" if "mes" in df.columns else None)
            if not mc:
                continue
            df[col_v] = pd.to_numeric(df[col_v], errors="coerce").fillna(0)
            cur, base, lab = trim3(df, col_v, mc)
            tot, totb = float(cur[col_v].sum()), float(base[col_v].sum())
            out[f"{key}_ult3m"] = int(tot)
            out[f"{key}_ult3m_yoy"] = round((tot - totb) / max(totb, 1), 3)
            out[f"{key}_ventana"] = lab
    except Exception as e:
        print(f"[transform][WARN] kpis_ult3m: {e}")
    return out

def kpis_desglose() -> dict:
    """Todos los cortes posibles por fuente. Escribe desglose_*.csv en processed."""
    out: dict = {}
    try:
        # Género entradas/salidas por año
        for key, tag in (("entradas_nacionalidad", "entradas"), ("salidas_destino", "salidas")):
            df = latest_raw(key)
            if df.empty or not {"femenino", "masculino"}.issubset(df.columns):
                continue
            df["femenino"] = pd.to_numeric(df["femenino"], errors="coerce").fillna(0)
            df["masculino"] = pd.to_numeric(df["masculino"], errors="coerce").fillna(0)
            g = df.groupby(df["a_o"].astype(str))[["femenino", "masculino"]].sum()
            g["pct_fem"] = (g["femenino"] / (g["femenino"] + g["masculino"]).replace(0, 1)).round(3)
            g.to_csv(PROC / f"desglose_genero_{tag}.csv")
            r = g.loc[str(g.index.max())]
            out[f"genero_{tag}_fem"] = float(r["pct_fem"])
        # Rutas + aerolíneas + carga MDE (último año completo de la serie aérea)
        aer = latest_raw("aereo_mde_eoh")
        if not aer.empty:
            aer["pasajeros"] = pd.to_numeric(aer.get("pasajeros", 0), errors="coerce").fillna(0)
            lleg = aer[aer.get("sentido", "") == "llegada"].copy()
            y1 = str(sorted(lleg["a_o"].astype(str).unique())[-2])
            l1 = lleg[lleg["a_o"].astype(str) == y1]
            rutas = l1.groupby("ciudad_origen")["pasajeros"].sum().sort_values(ascending=False).head(15)
            rutas.to_csv(PROC / "desglose_rutas_mde.csv", header=["pax"])
            out["rutas_top1"] = str(rutas.index[0]) if len(rutas) else ""
            if "nombre" in l1.columns:
                aero = l1.groupby("nombre")["pasajeros"].sum().sort_values(ascending=False).head(10)
                aero.to_csv(PROC / "desglose_aerolineas.csv", header=["pax"])
                out["aerolinea_top1"] = str(aero.index[0]) if len(aero) else ""
            if "carga_correo_kg" in lleg.columns:
                lleg["carga_correo_kg"] = pd.to_numeric(lleg["carga_correo_kg"], errors="coerce").fillna(0)
                car = lleg.groupby(lleg["a_o"].astype(str))["carga_correo_kg"].sum()
                car.to_csv(PROC / "desglose_carga_mde.csv", header=["kg"])
                out["carga_ult_kg"] = float(car.iloc[-1])
            if "tr_fico_n_i" in lleg.columns:
                nac_int = lleg.groupby([lleg["a_o"].astype(str), "tr_fico_n_i"])["pasajeros"].sum().unstack(fill_value=0)
                nac_int.to_csv(PROC / "desglose_nac_int.csv")
        # Estacionalidad mensual Medellín (2024-2026)
        med = latest_raw("medellin_no_residentes")
        if not med.empty:
            med["cant_extranjeros_no_residentes"] = pd.to_numeric(med["cant_extranjeros_no_residentes"], errors="coerce").fillna(0)
            med["mes_n"] = med["mes"].astype(str).str.strip().str.lower().map(MES)
            est = med.groupby([med["a_o"].astype(str), "mes_n"])["cant_extranjeros_no_residentes"].sum().reset_index()
            est.to_csv(PROC / "desglose_estacionalidad.csv", index=False)
            mmax = est.loc[est["cant_extranjeros_no_residentes"].idxmax()]
            out["mes_pico"] = f"{int(mmax['mes_n']):02d}-{mmax['a_o']}"
        # PITS y sitios (baseline MEData)
        pits = latest_raw("medata_pits")
        if not pits.empty and {"pit_nombre", "pit_totalvisitas"}.issubset(pits.columns):
            pits["pit_totalvisitas"] = pd.to_numeric(pits["pit_totalvisitas"], errors="coerce").fillna(0)
            pt = pits.groupby("pit_nombre")["pit_totalvisitas"].sum().sort_values(ascending=False).head(10)
            pt.to_csv(PROC / "desglose_pits.csv", header=["visitas"])
            out["pits_top1"] = str(pt.index[0]) if len(pt) else ""
        sit = latest_raw("medata_sitios_interes")
        if not sit.empty and {"sit_nombre", "sit_totalvisitas"}.issubset(sit.columns):
            sit["sit_totalvisitas"] = pd.to_numeric(sit["sit_totalvisitas"], errors="coerce").fillna(0)
            st_ = sit.groupby("sit_nombre")["sit_totalvisitas"].sum().sort_values(ascending=False).head(10)
            st_.to_csv(PROC / "desglose_sitios.csv", header=["visitas"])
            out["sitio_top1"] = str(st_.index[0]) if len(st_) else ""
        # Alojamiento + pernoctación DANE último trimestre
        for f, csvn in (("dane_egit_alojamiento", "desglose_alojamiento"), ("dane_egit_pernoctacion", "desglose_pernoct")):
            df = latest_raw(f)
            if df.empty:
                continue
            last = df["trimestre"].dropna().unique().tolist()[-1]
            sub = df[df["trimestre"] == last].filter(["concepto", "valor"]).copy()
            sub["valor"] = pd.to_numeric(sub["valor"], errors="coerce")
            sub.to_csv(PROC / f"{csvn}.csv", index=False)
        # Uplift eventos: Feria vs promedio mensual mismo año (baseline)
        fer = latest_raw("medata_occ_feria")
        occ = latest_raw("medata_ocupacion_med")
        if not fer.empty and not occ.empty:
            up = []
            for f_, tag in ((fer, "feria"), (occ, "base")):
                pc = [c for c in f_.columns if "periodo" in c.lower()][0]
                vc = [c for c in f_.columns if "valor" in c.lower()][0]
                d = f_.copy()
                d["ano"] = d[pc].astype(str).str.slice(0, 4)
                up.append(d.groupby("ano")[vc].mean().rename(tag))
            uplift = pd.concat(up, axis=1).dropna()
            uplift["uplift_pp"] = (uplift["feria"] - uplift["base"]).round(1)
            uplift.to_csv(PROC / "desglose_uplift_feria.csv")
            out["uplift_feria_pp"] = float(uplift["uplift_pp"].iloc[-1]) if len(uplift) else 0
        # Trends momentum: últimas 4 sem vs 4 previas por geo
        tre = latest_raw("google_trends")
        if not tre.empty:
            t = tre.copy()
            t["date"] = pd.to_datetime(t["date"])
            t = t.sort_values("date")
            mom = {}
            for geo, g in t.groupby("geo"):
                cols = [c for c in g.columns if "Medell" in c]
                s = g.groupby("date")[cols].sum().sum(axis=1).sort_index()
                if len(s) >= 8:
                    mom[str(geo)] = round(float(s.tail(4).mean() - s.iloc[-8:-4].mean()), 1)
            pd.Series(mom, name="momentum").to_csv(PROC / "desglose_trends_momentum.csv", header=True)
            out["momentum_top_geo"] = max(mom, key=mom.get) if mom else ""
        # Alertas por fuente + serie semanal
        al = latest_raw("alerts_rss")
        if not al.empty:
            al["es_reddit"] = al["feed"].astype(str).str.contains("reddit")
            src = al.groupby("es_reddit").size()
            src.to_csv(PROC / "desglose_alertas_fuente.csv", header=["n"])
            al["fecha"] = pd.to_datetime(al["fecha"], errors="coerce", utc=True)
            sem = al.dropna(subset=["fecha"]).groupby(al["fecha"].dt.strftime("%Y-W%V")).size()
            sem.to_csv(PROC / "desglose_alertas_serie.csv", header=["n"])
            out["alertas_sem_max"] = int(sem.max()) if len(sem) else 0
        # Salidas top por país último año completo
        sal = latest_raw("salidas_destino")
        if not sal.empty:
            sal["pais"] = sal["pa_s_destino"].map(norm_pais)
            sal["total"] = pd.to_numeric(sal["total"], errors="coerce").fillna(0)
            y1 = str(sorted(sal["a_o"].astype(str).unique())[-2])
            top = sal[sal["a_o"].astype(str) == y1].groupby("pais")["total"].sum().sort_values(ascending=False).head(12)
            top.to_csv(PROC / "desglose_salidas_top.csv", header=["salidas"])
            out["salidas_top1"] = str(top.index[0]) if len(top) else ""
    except Exception as e:
        print(f"[transform][WARN] kpis_desglose: {e}")
    return out

def _eu_ult_sum(df: pd.DataFrame) -> float:
    """Suma de la columna numerica disponible en el ultimo time (T2)."""
    tcol = next((c for c in df.columns if c.lower() in ("time", "year", "a_o", "periodo", "fecha")), None)
    ncols = [c for c in df.columns if c != tcol and pd.to_numeric(df[c], errors="coerce").notna().any()]
    if not ncols:
        raise ValueError("sin columna numerica")
    d = df.copy()
    d["_v"] = pd.to_numeric(d[ncols[0]], errors="coerce")
    if tcol is not None:
        d = d[d[tcol] == d[tcol].max()]
    return float(d["_v"].fillna(0).sum())


def _seg_ult(df: pd.DataFrame) -> int:
    """Filas del ultimo mes si trae fecha, si no total (T2)."""
    fcol = next((c for c in df.columns if "fecha" in c.lower()), None)
    if fcol is None:
        return int(len(df))
    f = pd.to_datetime(df[fcol], errors="coerce").dropna()
    if f.empty:
        return int(len(df))
    return int((f.dt.strftime("%Y-%m") == f.dt.strftime("%Y-%m").max()).sum())


def kpis_nuevas() -> dict:
    """T2 (S1,S2): agrega las fuentes arrastradas con datos pero sin KPI.
    Un try/except por fuente: si falta el CSV, SKIP individual sin tumbar el run."""
    out: dict = {}
    try:  # 1. wb_receipts: gasto emisor top (max RCPT.CD ultimo anio con dato) + COL mismo anio
        df = latest_raw("wb_receipts")
        if not df.empty and {"value", "indicator", "year"} <= set(df.columns):
            df = df.copy()
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            rcpt = df[df["indicator"].astype(str).str.contains("RCPT", na=False)].dropna(subset=["value"])
            if not rcpt.empty:
                sub = rcpt[rcpt["year"] == rcpt["year"].max()]
                out["gasto_emisor_top_usd"] = float(sub["value"].max())
                co = sub[sub["countryiso3code"].astype(str) == "COL"]["value"] if "countryiso3code" in sub.columns else sub["value"].iloc[0:0]
                if not co.empty:
                    out["gasto_emisor_co_usd"] = float(co.iloc[0])
    except Exception as e:
        print(f"[transform][SKIP] wb_receipts: {e}")
    try:  # 2. wb_departures: salidas COL ultimo anio con dato (ST.INT.DPRT)
        df = latest_raw("wb_departures")
        if not df.empty and {"value", "year"} <= set(df.columns):
            df = df.copy()
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            if "indicator" in df.columns:
                df = df[df["indicator"].astype(str).str.contains("DPRT", na=False)]
            if "countryiso3code" in df.columns:
                df = df[df["countryiso3code"].astype(str) == "COL"]
            df = df.dropna(subset=["value"])
            if not df.empty:
                out["salidas_col_total"] = float(df[df["year"] == df["year"].max()]["value"].iloc[0])
    except Exception as e:
        print(f"[transform][SKIP] wb_departures: {e}")
    for _name, _key in (("eurostat_tourism", "noches_eu_total"),
                         ("eurostat_capacity", "camas_eu_total"),
                         ("eurostat_demanda", "demanda_eu_viajes")):
        try:  # 3-5. Eurostat: parse defensivo, dataset trazadora ignorada
            df = latest_raw(_name)
            if not df.empty:
                out[_key] = _eu_ult_sum(df)
        except Exception as e:
            print(f"[transform][SKIP] {_name}: {e}")
    try:  # 6. eurostat_aviation: pax ES ultimo time
        df = latest_raw("eurostat_aviation")
        if not df.empty and "geo" in df.columns:
            pcol = [c for c in df.columns if "pass" in c.lower()][0]
            df = df.copy()
            df["passengers"] = pd.to_numeric(df[pcol], errors="coerce")
            es = df[df["geo"].astype(str).str.contains("spain", case=False, na=False)].dropna(subset=["passengers"])
            if not es.empty:
                out["pax_eu_es"] = float(es[es["time"] == es["time"].max()]["passengers"].max())
    except Exception as e:
        print(f"[transform][SKIP] eurostat_aviation: {e}")
    try:  # 7. RNT: filas
        out["rnt_med_total"] = int(len(latest_raw("rnt_prestadores")))
    except Exception as e:
        print(f"[transform][SKIP] rnt_prestadores: {e}")
    try:
        out["rnt_ant_total"] = int(len(latest_raw("rnt_antioquia")))
    except Exception as e:
        print(f"[transform][SKIP] rnt_antioquia: {e}")
    try:  # 8. seguridad: filas ultimo mes
        df = latest_raw("seguridad_hurtos_med")
        if not df.empty:
            out["hurtos_med_ult"] = _seg_ult(df)
    except Exception as e:
        print(f"[transform][SKIP] seguridad_hurtos_med: {e}")
    try:
        df = latest_raw("seguridad_homicidios_med")
        if not df.empty:
            out["homicidios_med_ult"] = _seg_ult(df)
    except Exception as e:
        print(f"[transform][SKIP] seguridad_homicidios_med: {e}")
    try:  # 9. ideam lluvia: ultimo valor numerico por fecha
        df = latest_raw("ideam_lluvia_med")
        if not df.empty:
            vcol = next((c for c in df.columns if "valor" in c.lower()), None)
            fcol = next((c for c in df.columns if "fecha" in c.lower()), None)
            if vcol:
                df = df.copy()
                df["_v"] = pd.to_numeric(df[vcol], errors="coerce")
                df = df.dropna(subset=["_v"])
                if not df.empty:
                    if fcol:
                        df = df.sort_values(fcol)
                    out["lluvia_med_mm"] = float(df["_v"].iloc[-1])
    except Exception as e:
        print(f"[transform][SKIP] ideam_lluvia_med: {e}")
    try:  # 9b. aire: ultimo pm2_5
        df = latest_raw("aire_med")
        if not df.empty:
            vcol = next((c for c in df.columns if "pm2" in c.lower()), None)
            if vcol:
                df = df.copy()
                df["_v"] = pd.to_numeric(df[vcol], errors="coerce")
                df = df.dropna(subset=["_v"])
                if not df.empty:
                    dcol = next((c for c in df.columns if "date" in c.lower() or "fecha" in c.lower()), None)
                    if dcol:
                        df = df.sort_values(dcol)
                    out["pm25_med"] = float(df["_v"].iloc[-1])
    except Exception as e:
        print(f"[transform][SKIP] aire_med: {e}")
    try:  # 10. terminales: suma pasajeros ultima ventana (columna defensiva)
        df = latest_raw("terminales_med")
        if not df.empty:
            vcol = next((c for c in ("pasajeros", "vehiculos") if c in df.columns
                         and pd.to_numeric(df[c], errors="coerce").notna().any()), None)
            if vcol:
                df = df.copy()
                df["_v"] = pd.to_numeric(df[vcol], errors="coerce").fillna(0)
                df["_m"] = df["mes"].astype(str).str.strip().str.lower().map(MES) if "mes" in df.columns else pd.NA
                df["_y"] = pd.to_numeric(df["a_o"], errors="coerce") if "a_o" in df.columns else pd.NA
                if pd.Series(df["_m"]).notna().any() and pd.Series(df["_y"]).notna().any():
                    df = df.dropna(subset=["_m", "_y"])
                    df = df[(df["_y"] == df["_y"].max()) & (df["_m"] == df[df["_y"] == df["_y"].max()]["_m"].max())]
                out["pax_terminal_mes"] = int(df["_v"].sum())
    except Exception as e:
        print(f"[transform][SKIP] terminales_med: {e}")
    try:  # 11. metro: suma ultimo periodo numerico disponible
        df = latest_raw("movilidad_metro_med")
        if not df.empty:
            pcol = next((c for c in df.columns if "period" in c.lower()), None)
            vcol = next((c for c in df.columns if c != pcol
                         and pd.to_numeric(df[c], errors="coerce").notna().any()), None)
            if vcol:
                df = df.copy()
                df["_v"] = pd.to_numeric(df[vcol], errors="coerce").fillna(0)
                if pcol:
                    df = df[df[pcol] == df[pcol].max()]
                out["pax_metro_mes"] = int(df["_v"].sum())
    except Exception as e:
        print(f"[transform][SKIP] movilidad_metro_med: {e}")
    try:  # 12. prensa: filas; wiki: suma views o filas
        out["menciones_prensa_7d"] = int(len(latest_raw("prensa_rss")))
    except Exception as e:
        print(f"[transform][SKIP] prensa_rss: {e}")
    try:
        df = latest_raw("wikimedia_views")
        if not df.empty:
            vcol = next((c for c in df.columns if "view" in c.lower()), None)
            v = pd.to_numeric(df[vcol], errors="coerce") if vcol else None
            out["interes_wiki_30d"] = int(v.fillna(0).sum()) if v is not None and v.notna().any() else int(len(df))
    except Exception as e:
        print(f"[transform][SKIP] wikimedia_views: {e}")
    try:  # 13. TRM: ultimo valor numerico
        df = latest_raw("trm_co")
        if not df.empty:
            vcol = next((c for c in df.columns if "rate" in c.lower() or "valor" in c.lower() or "trm" in c.lower()), None)
            if vcol is None:
                vcol = next((c for c in df.columns
                             if pd.to_numeric(df[c], errors="coerce").notna().any()), None)
            if vcol:
                v = pd.to_numeric(df[vcol], errors="coerce").dropna()
                if not v.empty:
                    out["trm_hoy"] = float(v.iloc[-1])
    except Exception as e:
        print(f"[transform][SKIP] trm_co: {e}")
    try:  # 14. festivos: filas del anio
        out["festivos_co_ano"] = int(len(latest_raw("festivos_co")))
    except Exception as e:
        print(f"[transform][SKIP] festivos_co: {e}")
    try:  # 15. aerocivil: suma pasajeros si existe, si no filas (dataset trazador ignorado)
        df = latest_raw("aerocivil_flota")
        if not df.empty:
            if "pasajeros" in df.columns and pd.to_numeric(df["pasajeros"], errors="coerce").notna().any():
                out["pax_aerocivil_total"] = int(pd.to_numeric(df["pasajeros"], errors="coerce").fillna(0).sum())
            else:
                out["pax_aerocivil_total"] = int(len(df))
    except Exception as e:
        print(f"[transform][SKIP] aerocivil_flota: {e}")
    return out


def kpis_emisores() -> dict:
    """T1 (S2,S3): escalares emisores/destinos/outbound SOLO desde PROC.
    Lee pais_dashboard.csv y destinos_dashboard.csv; SKIP individual, jamas tumba el run."""
    out: dict = {}
    try:
        p = PROC / "pais_dashboard.csv"
        d = PROC / "destinos_dashboard.csv"
        pai = pd.read_csv(p) if p.exists() else pd.DataFrame()
        des = pd.read_csv(d) if d.exists() else pd.DataFrame()
    except Exception as e:
        print(f"[transform][SKIP] kpis_emisores read: {e}")
        return {}
    try:  # Emisores desde pais_dashboard
        if not pai.empty:
            y1 = str(pai["ano_ref"].iloc[0]) if "ano_ref" in pai.columns else ""
            c_med, c_nac, c_sal = f"med_{y1}", f"nac_{y1}", f"sal_{y1}"
            df = pai.copy()
            for c in (c_med, c_nac, c_sal):
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
            if c_med in df.columns:
                df = df.sort_values(c_med, ascending=False).reset_index(drop=True)
                for i, tag in ((0, "top1"), (1, "top2"), (2, "top3")):
                    if len(df) > i:
                        out[f"emisor_{tag}"] = str(df.loc[i, "pais"])
                        out[f"emisor_{tag}_med"] = float(df.loc[i, c_med])
                tot = float(df[c_med].sum())
                if len(df) >= 5:
                    out["emisor_top5_share"] = round(float(df[c_med].head(5).sum()) / max(tot, 1), 4)
                yoy_col = "med_yoy" if "med_yoy" in df.columns else None
                if yoy_col:
                    df["_yoy"] = pd.to_numeric(df[yoy_col], errors="coerce")
                    cand = df[df[c_med] > 1000].dropna(subset=["_yoy"])
                    if not cand.empty:
                        best = cand.sort_values("_yoy", ascending=False).iloc[0]
                        out["emisor_crec_top"] = str(best["pais"])
                        out["emisor_crec_top_yoy"] = float(best["_yoy"])
    except Exception as e:
        print(f"[transform][SKIP] kpis_emisores emisores: {e}")
    try:  # Destinos desde destinos_dashboard
        if not des.empty:
            y1 = str(des["ano_ref"].iloc[0]) if "ano_ref" in des.columns else ""
            c_lle = f"llegadas_{y1}"
            if c_lle not in des.columns:
                num = [c for c in des.columns if c.startswith("llegadas_") and not c.endswith("_ytd")]
                c_lle = num[0] if num else None
            df = des.copy()
            if c_lle:
                df[c_lle] = pd.to_numeric(df[c_lle], errors="coerce").fillna(0)
                df = df.sort_values(c_lle, ascending=False).reset_index(drop=True)
                out["destino_top"] = str(df.loc[0, "ciudad"])
                out["destino_top_valor"] = float(df.loc[0, c_lle])
                med = df[df["ciudad"].astype(str).str.contains("Medell", na=False)]
                if not med.empty and "share" in df.columns:
                    out["destino_med_share"] = float(pd.to_numeric(med["share"], errors="coerce").fillna(0).iloc[0])
                elif not med.empty:
                    out["destino_med_share"] = round(float(med[c_lle].iloc[0]) / max(float(df[c_lle].sum()), 1), 4)
                if "yoy" in df.columns:
                    df["_yoy"] = pd.to_numeric(df["yoy"], errors="coerce")
                    cand = df.dropna(subset=["_yoy"])
                    if not cand.empty:
                        best = cand.sort_values("_yoy", ascending=False).iloc[0]
                        out["destino_crec_top"] = str(best["ciudad"])
                        out["destino_crec_top_yoy"] = float(best["_yoy"])
    except Exception as e:
        print(f"[transform][SKIP] kpis_emisores destinos: {e}")
    try:  # Outbound desde pais_dashboard (columna sal_*)
        if not pai.empty:
            y1 = str(pai["ano_ref"].iloc[0]) if "ano_ref" in pai.columns else ""
            c_sal = f"sal_{y1}"
            if c_sal in pai.columns:
                df = pai.copy()
                df[c_sal] = pd.to_numeric(df[c_sal], errors="coerce").fillna(0)
                out["salidas_total"] = float(df[c_sal].sum())
                df = df.sort_values(c_sal, ascending=False).reset_index(drop=True)
                out["salidas_top_dest"] = str(df.loc[0, "pais"])
                out["salidas_top_valor"] = float(df.loc[0, c_sal])
                if "sal_yoy" in df.columns:
                    out["salidas_top_yoy"] = float(pd.to_numeric(df.loc[0, "sal_yoy"], errors="coerce"))
    except Exception as e:
        print(f"[transform][SKIP] kpis_emisores outbound: {e}")
    return out


def kpis_llm() -> dict:
    """Agrega clasificacion LLM: marca_llm.csv por categoria + escalares.
    Sin clasificacion_llm.csv (sin key) -> SKIP honesto con dict vacio."""
    out: dict = {}
    try:
        df = latest_raw("clasificacion_llm")
        if df.empty or "categoria" not in df.columns:
            print("[transform][SKIP] sin clasificacion_llm.csv -> capa LLM en 0 (falta GROQ_API_KEY)")
            return out
        df = df.copy()
        df["categoria"] = df["categoria"].astype(str).str.lower()
        df["sentimiento"] = df["sentimiento"].astype(str).str.lower()
        tot = max(len(df), 1)
        g = df.groupby("categoria")
        agg = pd.DataFrame({
            "n": g.size(),
            "share": (g.size() / tot).round(4),
            "pos": g.apply(lambda x: int((x["sentimiento"] == "pos").sum()), include_groups=False),
            "neu": g.apply(lambda x: int((x["sentimiento"] == "neu").sum()), include_groups=False),
            "neg": g.apply(lambda x: int((x["sentimiento"] == "neg").sum()), include_groups=False),
        })
        agg["sent_net"] = ((agg["pos"] - agg["neg"]) / agg["n"].replace(0, 1)).round(3)
        agg["top_topico"] = g["topico"].agg(
            lambda s: str(s.mode().iloc[0])[:60] if not s.mode().empty else "") if "topico" in df.columns else ""
        agg.to_csv(PROC / "marca_llm.csv")
        print(f"[transform] marca_llm: {len(agg)} categorias")
        top = agg["n"].idxmax()
        marca_cats = [c for c in ("marca", "mice", "vacacional") if c in agg.index]
        pm = df[df["categoria"].isin(marca_cats)] if marca_cats else df.iloc[0:0]
        n_pm = max(len(pm), 1)
        out = {
            "llm_menciones_clasif": int(len(df)),
            "llm_top_categoria": str(top),
            "llm_top_cat_share": round(float(agg.loc[top, "share"]), 4),
            "llm_sent_net": round(float((df["sentimiento"] == "pos").sum() - (df["sentimiento"] == "neg").sum()) / tot, 3),
            "llm_sent_marca": round(float((pm["sentimiento"] == "pos").sum() - (pm["sentimiento"] == "neg").sum()) / n_pm, 3),
            "llm_share_seguridad": round(float(agg.loc["seguridad", "share"]) if "seguridad" in agg.index else 0.0, 4),
            "llm_top_topico": str(df["topico"].mode().iloc[0])[:60] if "topico" in df.columns and not df["topico"].mode().empty else "",
        }
    except Exception as e:
        print(f"[transform][SKIP] kpis_llm: {e}")
    return out


def kpis_amadeus() -> dict:  # type: ignore[no-untyped-def]
    """T1 (S2): ofertas Amadeus dev: conteos + precio mediano por ruta + periodo.
    Sin CSV -> ceros (SKIP honesto), nunca levanta. Patron kpis_p1."""
    try:
        df = latest_raw("amadeus_ofertas")
        if df.empty or not {"origen", "destino", "precio"} <= set(df.columns):  # type: ignore[attr-defined]
            print("[transform][SKIP] amadeus_ofertas: sin CSV -> 0")
            return {"amadeus_ofertas_total": 0, "amadeus_rutas": 0}
        df = df.copy()  # type: ignore[assignment]
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce")  # type: ignore[call-overload]
        df = df.dropna(subset=["precio"])  # type: ignore[assignment]
        if df.empty:  # type: ignore[attr-defined]
            return {"amadeus_ofertas_total": 0, "amadeus_rutas": 0}
        df["ruta"] = df["origen"].astype(str) + "_" + df["destino"].astype(str)  # type: ignore[attr-defined]
        out: dict = {"amadeus_ofertas_total": int(len(df)),  # type: ignore[arg-type]
                       "amadeus_rutas": int(df["ruta"].nunique())}  # type: ignore[attr-defined]
        if "periodo" in df.columns:  # type: ignore[attr-defined]
            out["amadeus_periodo"] = str(df["periodo"].max())  # type: ignore[attr-defined]
        med = df.groupby("ruta")["precio"].median()  # type: ignore[attr-defined]
        for ruta, val in med.items():
            key = "amadeus_mediana_" + "".join(c if c.isalnum() else "_" for c in str(ruta))
            out[key] = round(float(val), 2)
        return out
    except Exception as e:
        print(f"[transform][SKIP] amadeus_ofertas: {e}")
        return {"amadeus_ofertas_total": 0, "amadeus_rutas": 0}


def kpis_brand24() -> dict:  # type: ignore[no-untyped-def]
    """T2 (S3): menciones Brand24 trial: conteos + share por fuente + sentimiento neto.
    Sin CSV -> ceros (SKIP honesto), nunca levanta. Patron kpis_amadeus."""
    try:
        df = latest_raw("brand24_menciones")
        if df.empty or not {"fuente", "sentimiento"} <= set(df.columns):  # type: ignore[attr-defined]
            print("[transform][SKIP] brand24_menciones: sin CSV -> 0")
            return {"brand24_menciones_total": 0, "brand24_sentimiento_neto": 0.0}
        df = df.copy()  # type: ignore[assignment]
        total = int(len(df))  # type: ignore[arg-type]
        sent = df["sentimiento"].astype(str).str.strip().str.lower()  # type: ignore[attr-defined]
        pos = int(sent.isin({"pos", "positive", "positivo", "positiva"}).sum())
        neg = int(sent.isin({"neg", "negative", "negativo", "negativa"}).sum())
        out: dict = {"brand24_menciones_total": total,
                       "brand24_sentimiento_neto": round((pos - neg) / max(total, 1), 3)}
        if "alcance" in df.columns:  # type: ignore[attr-defined]
            out["brand24_alcance_total"] = int(
                pd.to_numeric(df["alcance"], errors="coerce").fillna(0).sum()  # type: ignore[call-overload]
            )
        if "periodo" in df.columns:  # type: ignore[attr-defined]
            out["brand24_periodo"] = str(df["periodo"].max())  # type: ignore[attr-defined]
        src = df["fuente"].astype(str).str.strip().str.lower()  # type: ignore[attr-defined]
        for name, cnt in src.value_counts().items():
            key = "brand24_share_" + "".join(c if c.isalnum() else "_" for c in str(name))
            out[key] = round(float(cnt) / max(total, 1), 3)
        return out
    except Exception as e:
        print(f"[transform][SKIP] brand24_menciones: {e}")
        return {"brand24_menciones_total": 0, "brand24_sentimiento_neto": 0.0}


def kpis_flightpowers() -> dict:  # type: ignore[no-untyped-def]
    """FlightPowers (reemplazo Amadeus, S1-S4): conteos + precio mediano por ruta + periodo.
    Sin CSV -> ceros (SKIP honesto), nunca levanta. Patron kpis_amadeus."""
    try:
        df = latest_raw("flightpowers_ofertas")
        if df.empty or not {"origen", "destino", "precio"} <= set(df.columns):  # type: ignore[attr-defined]
            print("[transform][SKIP] flightpowers_ofertas: sin CSV -> 0")
            return {"flightpowers_ofertas_total": 0, "flightpowers_rutas": 0}
        df = df.copy()  # type: ignore[assignment]
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce")  # type: ignore[call-overload]
        df = df.dropna(subset=["precio"])  # type: ignore[assignment]
        if df.empty:  # type: ignore[attr-defined]
            return {"flightpowers_ofertas_total": 0, "flightpowers_rutas": 0}
        df["ruta"] = df["origen"].astype(str) + "_" + df["destino"].astype(str)  # type: ignore[attr-defined]
        out: dict = {"flightpowers_ofertas_total": int(len(df)),  # type: ignore[arg-type]
                       "flightpowers_rutas": int(df["ruta"].nunique())}  # type: ignore[attr-defined]
        if "periodo" in df.columns:  # type: ignore[attr-defined]
            out["flightpowers_periodo"] = str(df["periodo"].max())  # type: ignore[attr-defined]
        med = df.groupby("ruta")["precio"].median()  # type: ignore[attr-defined]
        for ruta, val in med.items():
            key = "flightpowers_mediana_" + "".join(c if c.isalnum() else "_" for c in str(ruta))
            out[key] = round(float(val), 2)
        return out
    except Exception as e:
        print(f"[transform][SKIP] flightpowers_ofertas: {e}")
        return {"flightpowers_ofertas_total": 0, "flightpowers_rutas": 0}


def kpis_hoteles() -> dict:  # type: ignore[no-untyped-def]
    """T1 (S1-S3): hoteles FlightPowers: conteo + precio mediano + periodo.
    Sin CSV -> ceros (SKIP honesto), nunca levanta. Patron kpis_flightpowers."""
    try:
        df = latest_raw("flightpowers_hoteles")
        if df.empty or not {"ciudad", "hotel", "precio"} <= set(df.columns):  # type: ignore[attr-defined]
            print("[transform][SKIP] flightpowers_hoteles: sin CSV -> 0")
            return {"flightpowers_hoteles_total": 0}
        df = df.copy()  # type: ignore[assignment]
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce")  # type: ignore[call-overload]
        df = df.dropna(subset=["precio"])  # type: ignore[assignment]
        if df.empty:  # type: ignore[attr-defined]
            return {"flightpowers_hoteles_total": 0}
        out: dict = {"flightpowers_hoteles_total": int(len(df)),  # type: ignore[arg-type]
                       "flightpowers_hoteles_mediana": round(float(df["precio"].median()), 2)}  # type: ignore[attr-defined]
        if "periodo" in df.columns:  # type: ignore[attr-defined]
            out["flightpowers_hoteles_periodo"] = str(df["periodo"].max())  # type: ignore[attr-defined]
        return out
    except Exception as e:
        print(f"[transform][SKIP] flightpowers_hoteles: {e}")
        return {"flightpowers_hoteles_total": 0}


def kpis_aerodatabox() -> dict:  # type: ignore[no-untyped-def]
    """T1 (S1-S3): estado vuelos MDE/EOH: programados vs retrasados.
    Retrasado = retraso_min > 0 o estado delayed/cancelled/diverted.
    Sin CSV -> ceros (SKIP honesto), nunca levanta."""
    try:
        df = latest_raw("aerodatabox_mde")
        if df.empty or "estado" not in df.columns:  # type: ignore[attr-defined]
            print("[transform][SKIP] aerodatabox_mde: sin CSV -> 0")
            return {"aerodatabox_vuelos_total": 0, "aerodatabox_retrasados": 0}
        df = df.copy()  # type: ignore[assignment]
        total = int(len(df))  # type: ignore[arg-type]
        est = df["estado"].astype(str).str.strip().str.lower()  # type: ignore[attr-defined]
        ret = df["retraso_min"] if "retraso_min" in df.columns else 0  # type: ignore[attr-defined,assignment]
        ret = pd.to_numeric(ret, errors="coerce").fillna(0)  # type: ignore[call-overload]
        mal_estado = est.str.contains("delay|cancel|divert", na=False)
        retrasados = int(((ret > 0) | mal_estado).sum())
        out: dict = {"aerodatabox_vuelos_total": total,
                       "aerodatabox_retrasados": retrasados,
                       "aerodatabox_puntuales": total - retrasados}
        if "aeropuerto" in df.columns:  # type: ignore[attr-defined]
            out["aerodatabox_aeropuertos"] = int(df["aeropuerto"].nunique())  # type: ignore[attr-defined]
        return out
    except Exception as e:
        print(f"[transform][SKIP] aerodatabox_mde: {e}")
        return {"aerodatabox_vuelos_total": 0, "aerodatabox_retrasados": 0}


def kpis_operaciones() -> dict:  # type: ignore[no-untyped-def]
    """T2 (S1-S3): operaciones aereas Socrata jh8x-n6h6: total + top aeropuerto.
    Sin CSV -> ceros (SKIP honesto), nunca levanta. Columnas defensivas
    (el esquema Socrata puede variar): busca columna de valor y de aeropuerto."""
    try:
        df = latest_raw("operaciones_aereas")
        if df.empty:  # type: ignore[attr-defined]
            print("[transform][SKIP] operaciones_aereas: sin CSV -> 0")
            return {"operaciones_total": 0, "operaciones_top_aeropuerto": ""}
        df = df.copy()  # type: ignore[assignment]
        df.columns = [str(c).strip().lower() for c in df.columns]  # type: ignore[attr-defined]
        vcol = next((c for c in df.columns  # type: ignore[attr-defined]
                     if any(k in c for k in ("operacion", "vuelos", "total", "valor", "numero"))
                     and pd.to_numeric(df[c], errors="coerce").notna().any()), None)  # type: ignore[call-overload]
        acol = next((c for c in df.columns  # type: ignore[attr-defined]
                     if any(k in c for k in ("aeropuerto", "aerop", "origen", "destino", "ciudad"))), None)
        if vcol:
            df["_v"] = pd.to_numeric(df[vcol], errors="coerce").fillna(0)  # type: ignore[call-overload]
            total = int(df["_v"].sum())  # type: ignore[attr-defined]
        else:
            total = int(len(df))  # type: ignore[arg-type]
        top = ""
        if acol:
            g = df.groupby(df[acol].astype(str))["_v"].sum() if vcol else df[acol].astype(str).value_counts()  # type: ignore[attr-defined]
            top = str(g.idxmax()) if len(g) else ""  # type: ignore[attr-defined]
        return {"operaciones_total": total, "operaciones_top_aeropuerto": top}
    except Exception as e:
        print(f"[transform][SKIP] operaciones_aereas: {e}")
        return {"operaciones_total": 0, "operaciones_top_aeropuerto": ""}


def kpis_migrantes() -> dict:  # type: ignore[no-untyped-def]
    """T2 (S1-S3): migrantes a Colombia Socrata c4mm-qn8q: total + top nacionalidad.
    Sin CSV -> ceros (SKIP honesto), nunca levanta. Columnas defensivas."""
    try:
        df = latest_raw("migrantes_co")
        if df.empty:  # type: ignore[attr-defined]
            print("[transform][SKIP] migrantes_co: sin CSV -> 0")
            return {"migrantes_total": 0, "migrantes_top_nacionalidad": ""}
        df = df.copy()  # type: ignore[assignment]
        df.columns = [str(c).strip().lower() for c in df.columns]  # type: ignore[attr-defined]
        vcol = next((c for c in df.columns  # type: ignore[attr-defined]
                     if any(k in c for k in ("total", "migrantes", "cantidad", "valor", "numero"))
                     and pd.to_numeric(df[c], errors="coerce").notna().any()), None)  # type: ignore[call-overload]
        ncol = next((c for c in df.columns  # type: ignore[attr-defined]
                     if any(k in c for k in ("nacionalidad", "pais", "origen"))), None)
        if vcol:
            df["_v"] = pd.to_numeric(df[vcol], errors="coerce").fillna(0)  # type: ignore[call-overload]
            total = int(df["_v"].sum())  # type: ignore[attr-defined]
        else:
            total = int(len(df))  # type: ignore[arg-type]
        top = ""
        if ncol:
            g = df.groupby(df[ncol].astype(str))["_v"].sum() if vcol else df[ncol].astype(str).value_counts()  # type: ignore[attr-defined]
            top = str(g.idxmax()) if len(g) else ""  # type: ignore[attr-defined]
        return {"migrantes_total": total, "migrantes_top_nacionalidad": top}
    except Exception as e:
        print(f"[transform][SKIP] migrantes_co: {e}")
        return {"migrantes_total": 0, "migrantes_top_nacionalidad": ""}


def kpis_opentripmap() -> dict:  # type: ignore[no-untyped-def]
    """T3 (S1-S3): POIs turisticos OpenTripMap Medellin: total + top kind.
    Sin CSV -> ceros (SKIP honesto), nunca levanta. kinds viene como
    lista separada por comas ("cultural,museums"); se desagrega para el top."""
    try:
        df = latest_raw("opentripmap_med")
        if df.empty:  # type: ignore[attr-defined]
            print("[transform][SKIP] opentripmap_med: sin CSV -> 0")
            return {"opentripmap_pois_total": 0, "opentripmap_top_kind": ""}
        df = df.copy()  # type: ignore[assignment]
        df.columns = [str(c).strip().lower() for c in df.columns]  # type: ignore[attr-defined]
        total = int(len(df))  # type: ignore[arg-type]
        top = ""
        if "kinds" in df.columns:  # type: ignore[attr-defined]
            flat = []
            for cell in df["kinds"].astype(str):  # type: ignore[attr-defined]
                for k in cell.split(","):
                    k = k.strip().lower()
                    if k and k != "nan":
                        flat.append(k)
            if flat:
                top = str(pd.Series(flat).value_counts().idxmax())
        return {"opentripmap_pois_total": total, "opentripmap_top_kind": top}
    except Exception as e:
        print(f"[transform][SKIP] opentripmap_med: {e}")
        return {"opentripmap_pois_total": 0, "opentripmap_top_kind": ""}


def kpis_p1() -> dict:  # type: ignore[no-untyped-def]
    """T4 (S2,S3,S4): KPIs de la tanda P1 (EMA + Ticketmaster + OpenSky states).
    Un try/except por fuente: si falta el CSV, SKIP individual sin tumbar el run.
    Escribe desglose_ema.csv / desglose_eventos.csv en PROC
    (to_warehouse los espeja a web/data solo).
    NOTA tipos: pandas stubs incompletos (igual que el resto del archivo,
    verificado por ejecución); los ignores cubren solo este bloque nuevo."""
    out: dict = {}
    try:  # 1. EMA: ultimo periodo por indicador clave
        df = latest_raw("dane_ema")
        if not df.empty and {"periodo", "indicador", "valor"} <= set(df.columns):
            df = df.copy()  # type: ignore[assignment]
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce")  # type: ignore[call-overload]
            df = df.dropna(subset=["valor"])  # type: ignore[assignment]
            if not df.empty:  # type: ignore[attr-defined]
                ult = str(df["periodo"].max())  # type: ignore[attr-defined]
                out["ema_periodo"] = ult
                d = df[df["periodo"] == ult]  # type: ignore[assignment]
                # excluye variantes año-corrido/12-meses; deja var anual + niveles
                no12 = d[~d["indicador"].astype(str).str.contains("año corrido|12 meses", na=False)]  # type: ignore[assignment,attr-defined]
                pool = no12 if not no12.empty else d  # type: ignore[attr-defined]
                nac = pool[pool["indicador"].astype(str).str.contains("Total nacional", na=False)]  # type: ignore[assignment,attr-defined]
                ant = pool[pool["indicador"].astype(str).str.contains("Antioquia", na=False)]  # type: ignore[assignment,attr-defined]
                base = nac if not nac.empty else (ant if not ant.empty else pool)  # type: ignore[attr-defined]
                for pat, key in (("ingreso", "ema_ingresos_ult"),
                                  ("personal ocupado", "ema_personal_ult"),
                                  ("salario", "ema_salarios_ult"),
                                  ("ocupaci", "ema_ocupacion_ult")):
                    sub = base[base["indicador"].astype(str).str.contains(pat, case=False, na=False)]  # type: ignore[assignment,attr-defined]
                    if not sub.empty:  # type: ignore[attr-defined]
                        out[key] = float(sub["valor"].iloc[-1])  # type: ignore[attr-defined]
                piv = df.pivot_table(index="periodo", columns="indicador",  # type: ignore[attr-defined]
                                       values="valor", aggfunc="last")
                piv.to_csv(PROC / "desglose_ema.csv")  # type: ignore[attr-defined]
    except Exception as e:
        print(f"[transform][SKIP] dane_ema: {e}")
    try:  # 2. Ticketmaster: agenda proxima (hoy en adelante)
        df = latest_raw("ticketmaster_eventos")
        if not df.empty and "fecha" in df.columns:  # type: ignore[attr-defined]
            df = df.copy()  # type: ignore[assignment]
            hoy = date.today().isoformat()
            fut = df[df["fecha"].astype(str) >= hoy].sort_values("fecha")  # type: ignore[assignment,attr-defined]
            out["eventos_prox_total"] = int(len(fut))  # type: ignore[arg-type]
            if not fut.empty:  # type: ignore[attr-defined]
                out["eventos_prox_nombre"] = str(fut["nombre"].iloc[0])[:80]  # type: ignore[attr-defined]
                out["eventos_prox_fecha"] = str(fut["fecha"].iloc[0])  # type: ignore[attr-defined]
            fut.head(50).to_csv(PROC / "desglose_eventos.csv", index=False)  # type: ignore[attr-defined]
    except Exception as e:
        print(f"[transform][SKIP] ticketmaster_eventos: {e}")
    try:  # 3. OpenSky: snapshot states (sin flujos: /flights exige auth)
        df = latest_raw("opensky_states")
        if not df.empty:  # type: ignore[attr-defined]
            out["opensky_en_vuelo"] = int(len(df))  # type: ignore[arg-type]
    except Exception as e:
        print(f"[transform][SKIP] opensky: {e}")
    return out


def run():
    PROC.mkdir(parents=True, exist_ok=True)
    hoy = date.today().isoformat()
    trends = latest_raw("google_trends")
    alerts = latest_raw("alerts_rss")
    marca = kpis_marca(alerts)
    dem = kpis_demanda()
    dan = kpis_dane()
    gde = kpis_gdelt()
    mdt = kpis_medata()
    mex = kpis_medata_extra()
    pai = kpis_pais()
    des = kpis_destinos()
    emi = kpis_emisores()
    u3m = kpis_ult3m()
    dsg = kpis_desglose()
    nva = kpis_nuevas()
    llm = kpis_llm()
    p1 = kpis_p1()
    amd = kpis_amadeus()
    brd = kpis_brand24()
    flp = kpis_flightpowers()
    hot = kpis_hoteles()
    aero = kpis_aerodatabox()
    ope = kpis_operaciones()
    mig = kpis_migrantes()
    otp = kpis_opentripmap()
    print(f"[transform] trends={len(trends)} alerts={len(alerts)} marca={marca} dem={dem} dane={dan} gdelt={gde} medata={mdt} medata_extra={mex} paises={len(pai)} destinos={len(des)} emisores={emi} ult3m={u3m} desglose={dsg} nuevas={nva} llm={llm} p1={p1} amadeus={amd} brand24={brd} flightpowers={flp} hoteles={hot} aerodatabox={aero} operaciones={ope} migrantes={mig} opentripmap={otp}")

    # CRM interno (gated manual): si el Bureau deja su Excel en data/raw/manual/crm.xlsx se calculan KPIs MICE
    crm_path = RAW / "manual" / "crm.xlsx"
    mice = {}
    if crm_path.exists():
        crm = pd.read_excel(crm_path)
        # alias de columnas plantilla (gasto_prom_usd, estadia_noches, valor_rfp_usd)
        crm = crm.rename(columns={"gasto_prom_usd": "gasto_prom", "estadia_noches": "estadia", "valor_rfp_usd": "valor_rfp"})
        # espera columnas: estado (recibido/ganado), asistentes, gasto_prom, estadia, valor_rfp, prob
        rec = len(crm)
        gan = len(crm[crm.get("estado", "") == "ganado"]) if "estado" in crm.columns else 0
        mice = {
            "win_rate": round(gan / max(rec, 1), 3),
            "noches_mice": float((crm.get("asistentes", 0) * crm.get("estadia", 0)).sum()) if {"asistentes", "estadia"} <= set(crm.columns) else 0,
            "derrama_mice": float((crm.get("asistentes", 0) * crm.get("gasto_prom", 0) * crm.get("estadia", 0)).sum()) if {"asistentes", "gasto_prom", "estadia"} <= set(crm.columns) else 0,
            "pipeline_ponderado": float((crm.get("valor_rfp", 0) * crm.get("prob", 0)).sum()) if {"valor_rfp", "prob"} <= set(crm.columns) else 0,
        }
    else:
        print("[transform][SKIP] sin data/raw/manual/crm.xlsx -> KPIs MICE en 0 hasta carga manual")
        mice = {"win_rate": 0, "noches_mice": 0, "derrama_mice": 0, "pipeline_ponderado": 0}

    kpi = pd.DataFrame([{"fecha": hoy, **marca, **dem, **dan, **gde, **mdt, **mex, **mice, **emi, **u3m, **nva, **llm, **p1, **amd, **brd, **flp, **hot, **aero, **ope, **mig, **otp,
                           **{k: v for k, v in dsg.items() if isinstance(v, (int, float))}}])
    p = PROC / f"kpis_{hoy}.csv"
    kpi.to_csv(p, index=False)
    # acumulado para Power BI
    hist = PROC / "kpis_historico.csv"
    if hist.exists():
        h = pd.read_csv(hist)
        h = pd.concat([h, kpi], ignore_index=True).drop_duplicates(subset=["fecha"], keep="last")
    else:
        h = kpi
    h.to_csv(hist, index=False)
    print(f"[transform] KPIs -> {p} + historico ({len(h)} días)")
    return p

if __name__ == "__main__":
    run()
