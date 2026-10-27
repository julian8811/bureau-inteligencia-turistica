# Tablero Bureau Medellín — Reuniones / Vacacional / Marca
# Uso: streamlit run etl-bureau/dashboard/app.py
# Lee el warehouse local (sin Power BI, sin licencias, 100% Python).

import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RAW_TODAY = sorted((BASE / "data" / "raw").glob("20*"))[-1] if list((BASE / "data" / "raw").glob("20*")) else None
PROC = BASE / "data" / "processed"

st.set_page_config(page_title="Colmayor · Inteligencia Turística Medellín", layout="wide", page_icon="🌺")

# Línea gráfica I.U. Colegio Mayor de Antioquia — Manual de comunicaciones y mercadeo V7
# Paleta institucional: #172139 navy, #00AEAC turquesa, #E9901E naranja, #B4C42C lima, #108181 teal, #FBBB28 amarillo
# Tipografías: Montserrat (títulos/texto)
COLMAYOR_SEQ = ["#172139", "#00AEAC", "#E9901E", "#B4C42C", "#108181", "#FBBB28"]

st.markdown(
    """<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }
h1, h2, h3 { font-weight: 800 !important; color: #172139 !important; }
section[data-testid="stSidebar"] { background-color: #172139; }
section[data-testid="stSidebar"] * { color: white !important; }
div[data-testid="stMetric"] { background: #EEF1F5; border-left: 6px solid #E9901E; border-radius: 8px; padding: 8px 12px; }
</style>""",
    unsafe_allow_html=True,
)

logo = BASE / "dashboard" / "assets" / "logo_colmayor_navy.png"
if logo.exists():
    st.image(str(logo), use_container_width=True)

@st.cache_data
def load(name, day=None):
    d = day or (RAW_TODAY.name if RAW_TODAY else "")
    p = BASE / "data" / "raw" / d / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

@st.cache_data
def hist():
    p = PROC / "kpis_historico.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

H = hist()
st.title("Inteligencia Turística · Medellín y Antioquia")
st.caption("I.U. Colegio Mayor de Antioquia · Datos abiertos + CRM Bureau · "
           f"corte {RAW_TODAY.name if RAW_TODAY else '—'} · ETL diario Python")
st.divider()

tab_mice, tab_vac, tab_marca = st.tabs(["🤝 Reuniones (MICE)", "✈️ Vacacional", "📣 Marca Ciudad"])

# ============ REUNIONES ============
with tab_mice:
    c1, c2, c3, c4 = st.columns(4)
    if not H.empty:
        r = H.iloc[-1]
        c1.metric("Win rate RFP", f"{r.get('win_rate', 0)*100:.0f}%")
        c2.metric("Noches MICE", f"{r.get('noches_mice', 0):,.0f}")
        c3.metric("Derrama estimada", f"USD {r.get('derrama_mice', 0):,.0f}")
        c4.metric("Pipeline ponderado", f"USD {r.get('pipeline_ponderado', 0):,.0f}")
    st.subheader("Ocupación: semana de evento vs promedio")
    occ = load("medata_ocupacion_med")
    if not occ.empty:
        pcol = [c for c in occ.columns if "periodo" in c.lower()][0]
        vcol = [c for c in occ.columns if "valor" in c.lower()][0]
        occ = occ.sort_values(pcol)
        fig = px.bar(occ.tail(24), x=pcol, y=vcol, title="Ocupación hotelera mensual Medellín (%) — baseline MEData",
                     color_discrete_sequence=["#E9901E"])
        st.plotly_chart(fig, use_container_width=True)
    crm = pd.read_excel(BASE / "data" / "raw" / "manual" / "crm.xlsx", sheet_name=0) if (BASE / "data" / "raw" / "manual" / "crm.xlsx").exists() else pd.DataFrame()
    if not crm.empty:
        st.subheader("Pipeline RFP (CRM interno)")
        st.dataframe(crm, use_container_width=True)

# ============ VACACIONAL ============
with tab_vac:
    c1, c2, c3, c4 = st.columns(4)
    if not H.empty:
        r = H.iloc[-1]
        c1.metric("Extranjeros no residentes (acum.)", f"{r.get('llegadas_medellin_nr', 0):,.0f}")
        c2.metric("Top emisor", str(r.get('top1_emisor', '—')))
        c3.metric("Pax llegadas MDE (acum.)", f"{r.get('pax_llegadas_mde', 0):,.0f}")
        c4.metric("Gasto prom/día (DANE)", f"${r.get('gasto_prom_dia_cop', 0):,.0f} COP")
    col_a, col_b = st.columns(2)
    med = load("medellin_no_residentes")
    if not med.empty:
        top = med.groupby("paisoeeresidencia")["cant_extranjeros_no_residentes"].sum().sort_values(ascending=False).head(10)
        with col_a:
            st.plotly_chart(px.bar(top, title="Top 10 emisores a Medellín", color_discrete_sequence=["#172139"]), use_container_width=True)
    tr = load("google_trends")
    if not tr.empty:
        with col_b:
            t = tr.melt(id_vars=["date", "geo"], value_vars=[c for c in tr.columns if c not in ("date", "geo", "isPartial")],
                        var_name="búsqueda", value_name="índice")
            st.plotly_chart(px.line(t[t.geo == "US"], x="date", y="índice", color="búsqueda",
                                    title="Intención de búsqueda USA hacia Medellín"), use_container_width=True)
    st.subheader("Ocupación vs tarifa (baseline histórico)")
    occ = load("medata_ocupacion_med"); tar = load("medata_tarifa_med")
    if not occ.empty and not tar.empty:
        p1 = [c for c in occ.columns if "periodo" in c.lower()][0]; v1 = [c for c in occ.columns if "valor" in c.lower()][0]
        p2 = [c for c in tar.columns if "periodo" in c.lower()][0]; v2 = [c for c in tar.columns if "valor" in c.lower()][0]
        m = occ[[p1, v1]].merge(tar[[p2, v2]], left_on=p1, right_on=p2, how="inner")
        st.plotly_chart(px.scatter(m, x=v1, y=v2, title="Ocupación % vs tarifa COP (cada punto = un mes)",
                                   labels={v1: "Ocupación %", v2: "Tarifa COP"}, color_discrete_sequence=["#E9901E"]),
                        use_container_width=True)

# ============ MARCA ============
with tab_marca:
    c1, c2, c3 = st.columns(3)
    if not H.empty:
        r = H.iloc[-1]
        c1.metric("Menciones (7d)", f"{r.get('menciones', 0):,.0f}")
        c2.metric("Sentimiento neto", f"{r.get('sentimiento_neto', 0):+.2f}")
        c3.metric("Share Medellín", f"{r.get('share_medellin', 0)*100:.0f}%")
    al = load("alerts_rss")
    if not al.empty:
        st.subheader("Últimas menciones (Google News + Reddit, sin login)")
        st.dataframe(al[["fecha", "titulo", "link"]].head(20), use_container_width=True)

st.divider()
st.caption("I.U. Colegio Mayor de Antioquia · Vigilada MinEducación · Fuente ETL: datos.gov.co, DANE, MEData, Google Trends · Uso académico/institucional")
