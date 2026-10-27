"""Transform: raw diario -> modelo estrella + KPIs del Plan Dashboard (pestaña Excel).
Tablas: fact_demanda, fact_mice, fact_marca, dim_fecha, dim_mercado.
Fórmulas espejo del Excel: win_rate=ganados/recibidos, derrama=asist*gasto*estadía,
revpar=occ*adr, sentimiento=(pos-neg)/total, engagement=inter/alcance.
"""
from pathlib import Path
from datetime import date
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
        tre = latest_raw("google_trends")
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
    end = max_y, max_m
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
    pai = kpis_pais()
    des = kpis_destinos()
    u3m = kpis_ult3m()
    print(f"[transform] trends={len(trends)} alerts={len(alerts)} marca={marca} dem={dem} dane={dan} gdelt={gde} medata={mdt} paises={len(pai)} destinos={len(des)} ult3m={u3m}")

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

    kpi = pd.DataFrame([{"fecha": hoy, **marca, **dem, **dan, **gde, **mdt, **mice, **u3m}])
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
