"""Generador tablero estatico HTML+CSS puro (reemplazo Streamlit).

Lee el warehouse local y emite dashboard/index.html sin <script>,
sin servidor Python, imprimible (A4). Paridad con los 4 tabs Streamlit:
Reuniones / Vacacional / Marca / Por pais.
Uso: python etl-bureau/dashboard/build_html.py
"""
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
RAW = BASE / "data" / "raw"
OUT = Path(__file__).resolve().parent / "index.html"

CSS = """:root{--navy:#172139;--teal:#00AEAC;--orange:#E9901E;--lime:#B4C42C;--teal2:#108181;--yellow:#FBBB28;--mut:#5A6C7D}
*{box-sizing:border-box}body{font-family:Montserrat,Arial,sans-serif;color:var(--navy);margin:0;background:#fff;font-size:11pt}
@page{size:A4;margin:14mm 12mm}header{background:var(--navy);color:#fff;padding:22px 26px}
header h1{font-size:22pt;margin:10px 0 4px}header p{color:#cfd6df;font-size:10pt;margin:2px 0}
header img{width:100%;max-width:560px}main{max-width:1100px;margin:0 auto;padding:0 16px 30px}
nav.toc{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}nav.toc a{background:#EEF1F5;border-radius:20px;padding:6px 14px;color:var(--navy);text-decoration:none;font-weight:700;font-size:10pt}
h2{font-size:15pt;border-left:8px solid var(--orange);padding-left:10px;margin:24px 0 8px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
.kpi{background:#EEF1F5;border-left:6px solid var(--orange);border-radius:8px;padding:10px 14px}
.kpi .v{font-size:1.35rem;font-weight:800}.kpi .l{font-size:.75rem;color:var(--mut)}
table{width:100%;border-collapse:collapse;font-size:9pt;margin:8px 0}
th{background:var(--navy);color:#fff;text-align:left;padding:5px 7px}
td{padding:4px 7px;border-bottom:1px solid #e5e7eb}.num{text-align:right;font-variant-numeric:tabular-nums}
.bul{background:#EEF1F5;border-left:6px solid var(--orange);border-radius:6px;padding:8px 12px;margin:6px 0;font-size:10pt}
.src{font-size:8pt;color:var(--mut)}.foot{margin-top:18px;border-top:2px solid var(--navy);padding-top:6px;font-size:8pt;color:var(--mut)}
.sec{page-break-inside:avoid}@media print{nav.toc{display:none}header{padding:14px}main{padding:0}}
"""


def fmt(n) -> str:
    try:
        return f"{float(n):,.0f}".replace(",", ".")
    except Exception:
        return str(n if n == n else "—")


def pct(x) -> str:
    try:
        return f"{float(x) * 100:+.1f}%"
    except Exception:
        return "—"


def kpi(l, v) -> str:
    return f'<div class="kpi"><div class="v">{escape(str(v))}</div><div class="l">{escape(l)}</div></div>'


def table(head, rows) -> str:
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    tr = ""
    for r in rows:
        tds = "".join(
            f'<td class="num">{escape(str(c))}</td>' if isinstance(c, (int, float)) else f"<td>{escape(str(c))}</td>"
            for c in r
        )
        tr += f"<tr>{tds}</tr>"
    return f"<table><tr>{th}</tr>{tr}</table>"


def latest_raw(name: str) -> pd.DataFrame:
    cands = sorted(RAW.glob(f"*/{name}.csv"))
    if not cands:
        return pd.DataFrame()
    try:
        return pd.read_csv(cands[-1])
    except Exception:
        return pd.DataFrame()


def run() -> Path:
    hist = pd.read_csv(PROC / "kpis_historico.csv") if (PROC / "kpis_historico.csv").exists() else pd.DataFrame()
    r = hist.iloc[-1].to_dict() if not hist.empty else {}
    fecha = str(r.get("fecha", date.today().isoformat()))

    pais = pd.read_csv(PROC / "pais_dashboard.csv") if (PROC / "pais_dashboard.csv").exists() else pd.DataFrame()
    dest = pd.read_csv(PROC / "destinos_dashboard.csv") if (PROC / "destinos_dashboard.csv").exists() else pd.DataFrame()
    y1 = str(pais["ano_ref"].iloc[0]) if not pais.empty else "2025"
    c_med, c_nac = f"med_{y1}", f"nac_{y1}"

    alerts = latest_raw("alerts_rss")
    occ = latest_raw("medata_ocupacion_med")
    crm_p = RAW / "manual" / "crm.xlsx"
    crm = pd.read_excel(crm_p, sheet_name=0) if crm_p.exists() else pd.DataFrame()

    top_pais = pais.head(15) if not pais.empty else pd.DataFrame()
    top_dest = dest.head(12) if not dest.empty else pd.DataFrame()
    top_men = alerts.head(20) if not alerts.empty else pd.DataFrame()
    last_occ = occ.tail(12) if not occ.empty else pd.DataFrame()

    pcol = next((c for c in occ.columns if "periodo" in c.lower()), None) if not occ.empty else None
    vcol = next((c for c in occ.columns if "valor" in c.lower()), None) if not occ.empty else None

    s_mice = '<div class="kpis">' + "".join([
        kpi("Win rate RFP", f"{float(r.get('win_rate', 0)) * 100:.0f}%"),
        kpi("Noches MICE", fmt(r.get("noches_mice", 0))),
        kpi("Derrama estimada", f"USD {fmt(r.get('derrama_mice', 0))}"),
        kpi("Pipeline ponderado", f"USD {fmt(r.get('pipeline_ponderado', 0))}"),
    ]) + "</div>"
    t_crm = ""
    if not crm.empty:
        t_crm = "<h3>Pipeline RFP (CRM interno)</h3>" + table(
            list(map(str, crm.columns))[:6],
            crm.iloc[:20, :6].values.tolist(),
        )
    t_occ = ""
    if pcol and vcol and not last_occ.empty:
        t_occ = "<h3>Ocupación hotelera mensual Medellín (%) — baseline MEData</h3>" + table(
            ["Periodo", "Ocupación %"],
            [[str(a), round(float(b), 1)] for a, b in zip(last_occ[pcol].tolist(), last_occ[vcol].tolist())],
        )

    s_vac = '<div class="kpis">' + "".join([
        kpi("Extranjeros no residentes (acum.)", fmt(r.get("llegadas_medellin_nr", 0))),
        kpi("Top emisor", str(r.get("top1_emisor", "—"))),
        kpi("Pax llegadas MDE (acum.)", fmt(r.get("pax_llegadas_mde", 0))),
        kpi("Gasto prom/día (DANE)", f"${fmt(r.get('gasto_prom_dia_cop', 0))} COP"),
    ]) + "</div>"
    t_dest = ""
    if not top_dest.empty:
        t_dest = "<h3>Destinos Colombia — ranking</h3>" + table(
            ["Destino", f"Llegadas {y1}", "Share", "YoY"],
            [[str(a), fmt(b), f"{float(c) * 100:.1f}%", pct(d)]
             for a, b, c, d in zip(
                top_dest["ciudad"].tolist(),
                top_dest[f"llegadas_{y1}"].tolist(),
                top_dest["share"].tolist(),
                top_dest["yoy"].tolist())],
        )

    s_mar = '<div class="kpis">' + "".join([
        kpi("Menciones (7d)", fmt(r.get("menciones", 0))),
        kpi("Sentimiento neto", f"{float(r.get('sentimiento_neto', 0)):+.2f}"),
        kpi("Share Medellín", f"{float(r.get('share_medellin', 0)) * 100:.0f}%"),
    ]) + "</div>"
    t_men = ""
    if not top_men.empty and {"fecha", "titulo"}.issubset(top_men.columns):
        t_men = "<h3>Últimas menciones (Google News + Reddit, sin login)</h3>" + table(
            ["Fecha", "Titular"],
            [[str(a)[:16], str(b)] for a, b in zip(top_men["fecha"].tolist(), top_men["titulo"].tolist())],
        )

    s_pais = ""
    t_pais = ""
    if not top_pais.empty:
        s_pais = f'<p class="bul">Año de referencia {escape(y1)} · {len(pais)} países · top emisor {escape(str(top_pais.iloc[0]["pais"]))}</p>'
        t_pais = "<h3>Ranking por país emisor</h3>" + table(
            ["País", f"Medellín {y1}", "YoY Med", "Share Med", f"Colombia {y1}"],
            [[str(a), fmt(b), pct(c), f"{float(d) * 100:.1f}%", fmt(e)]
             for a, b, c, d, e in zip(
                top_pais["pais"].tolist(), top_pais[c_med].tolist(),
                top_pais["med_yoy"].tolist(), top_pais["share_med"].tolist(),
                top_pais[c_nac].tolist())],
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bureau Medellín · Tablero {escape(fecha)}</title>
<style>{CSS}</style>
</head>
<body>
<header>
<img src="assets/logo_colmayor_navy.png" alt="I.U. Colegio Mayor de Antioquia">
<h1>Inteligencia Turística · Medellín y Antioquia</h1>
<p>I.U. Colegio Mayor de Antioquia · Datos abiertos + CRM Bureau · corte {escape(fecha)} · ETL diario Python · HTML puro sin JS</p>
</header>
<main>
<nav class="toc"><a href="#mice">Reuniones</a><a href="#vac">Vacacional</a><a href="#marca">Marca</a><a href="#pais">Por país</a></nav>
<h2 id="mice">Reuniones (MICE)</h2><div class="sec">{s_mice}{t_occ}{t_crm}</div>
<h2 id="vac">Vacacional</h2><div class="sec">{s_vac}{t_dest}</div>
<h2 id="marca">Marca Ciudad</h2><div class="sec">{s_mar}{t_men}</div>
<h2 id="pais">Por país</h2><div class="sec">{s_pais}{t_pais}</div>
<p class="src">Fuente ETL: datos.gov.co, DANE, MEData, Google Trends · Uso académico/institucional</p>
<div class="foot">I.U. Colegio Mayor de Antioquia · Vigilada MinEducación · Generado automáticamente, cifras provisionales sujetas a ajuste.</div>
</main>
</body>
</html>"""
    OUT.write_text(html, encoding="utf-8")
    assert "<script" not in html.lower(), "HTML puro no debe incluir <script>"
    print(f"[dashboard] {OUT} ({len(html) // 1024} KB, fecha {fecha})")
    return OUT


if __name__ == "__main__":
    run()
