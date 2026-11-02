"""Generador tablero estatico HTML+CSS puro (reemplazo Streamlit).

Lee el warehouse local y emite dashboard/index.html sin <script>,
sin servidor Python, imprimible (A4). Set completo de KPIs (S4):
Reuniones / Vacacional / Marca+LLM / Emisores / Destinos+Outbound /
Territorio / Benchmark EU.
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
h3{font-size:11pt;margin:14px 0 4px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
.kpi{background:#EEF1F5;border-left:6px solid var(--orange);border-radius:8px;padding:10px 14px}
.kpi .v{font-size:1.35rem;font-weight:800}.kpi .l{font-size:.75rem;color:var(--mut)}
table{width:100%;border-collapse:collapse;font-size:9pt;margin:8px 0}
th{background:var(--navy);color:#fff;text-align:left;padding:5px 7px}
td{padding:4px 7px;border-bottom:1px solid #e5e7eb}.num{text-align:right;font-variant-numeric:tabular-nums}
.bul{background:#EEF1F5;border-left:6px solid var(--orange);border-radius:6px;padding:8px 12px;margin:6px 0;font-size:10pt}
.warn{background:#FDF3E3;border-left:6px solid var(--yellow);border-radius:6px;padding:8px 12px;margin:6px 0;font-size:10pt}
.src{font-size:8pt;color:var(--mut)}.foot{margin-top:18px;border-top:2px solid var(--navy);padding-top:6px;font-size:8pt;color:var(--mut)}
.sec{page-break-inside:avoid}.badge-hist{display:inline-block;background:#FDF3E3;border:1px solid var(--yellow);color:#7A5A00;border-radius:12px;padding:1px 10px;font-size:8pt;font-weight:700;margin-left:6px;white-space:nowrap}.kpi.hist{background:#FBF7EC;border-left-color:var(--yellow)}.kpi.hist .l{color:#7A5A00}@media print{nav.toc{display:none}header{padding:14px}main{padding:0}}
"""


def _na(x) -> bool:
    try:
        return bool(pd.isna(x))
    except Exception:
        return x is None


def fnum(x):
    """float(x) o None si falta/inválido (narrowing apto para pyright)."""
    if x is None or _na(x):
        return None
    try:
        return float(x)
    except Exception:
        return None


def fmt(n) -> str:
    if _na(n):
        return "—"
    try:
        return f"{float(n):,.0f}".replace(",", ".")
    except Exception:
        return str(n)


def pct(x) -> str:
    if _na(x):
        return "—"
    try:
        return f"{float(x) * 100:+.1f}%"
    except Exception:
        return "—"


def share(x) -> str:
    if _na(x):
        return "—"
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "—"


def sfmt(x, nd=2) -> str:
    if x is None or _na(x):
        return "—"
    try:
        return f"{float(x):+.{nd}f}"
    except Exception:
        return "—"


def txt(x) -> str:
    if _na(x) or str(x).strip() in ("", "nan", "None"):
        return "—"
    return str(x)


def kpi(label, value) -> str:
    return f'<div class="kpi"><div class="v">{escape(str(value))}</div><div class="l">{escape(label)}</div></div>'


def badge_hist(periodo) -> str:
    """Badge visible de baseline viejo. NaN-safe: sin período devuelve etiqueta genérica."""
    p = txt(periodo)
    if p == "—":
        return '<span class="badge-hist">baseline histórico</span>'
    return f'<span class="badge-hist">baseline histórico {escape(p)}</span>'


def kpi_hist(label, value, periodo) -> str:
    """KPI secundario: cifra vieja con badge visible, nunca como titular.

    La tarjeta nunca incluye cifras 2025/H1-2026: solo etiqueta + valor viejo + badge."""
    return (f'<div class="kpi hist"><div class="v">{escape(str(value))}</div>'
            f'<div class="l">{escape(label)} {badge_hist(periodo)}</div></div>')


def mes_corte_es(fecha) -> str:
    """'2026-10-29' -> 'oct-2026' (mes corriente del corte). NaN-safe."""
    try:
        s = str(fecha).strip()[:7]
        y, m = s.split("-")
        meses = {"01": "ene", "02": "feb", "03": "mar", "04": "abr", "05": "may", "06": "jun",
                 "07": "jul", "08": "ago", "09": "sep", "10": "oct", "11": "nov", "12": "dic"}
        if y.isdigit() and m in meses:
            return f"{meses[m]}-{y}"
    except Exception:
        return "—"
    return "—"


def es_trim_actual(tri) -> bool:
    """Trimestre de gasto vigente (contiene 2026) o baseline viejo."""
    try:
        return "2026" in str(tri)
    except Exception:
        return False


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


def _short_es(n) -> str:
    """Eje compacto es-CO: 378 mil · 1,1 M · 67,11 · 0,85. NaN-safe."""
    v = fnum(n)
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1_000_000:
        return f"{v / 1_000_000:.1f}".replace(".", ",").removesuffix(",0") + " M"
    if a >= 1_000:
        return f"{v / 1_000:.1f}".replace(".", ",").removesuffix(",0") + " mil"
    if abs(v - round(v)) < 1e-9:
        return fmt(v)
    return f"{v:.2f}".replace(".", ",")


def _pct_es(x) -> str:
    """Porcentaje es-CO con signo (+12,4%). NaN-safe."""
    v = fnum(x)
    if v is None:
        return "—"
    return f"{v * 100:+.1f}%".replace(".", ",")


def _p1_es(v) -> str:
    """Porcentaje es-CO a 1 decimal (67,1%). NaN-safe."""
    f = fnum(v)
    if f is None:
        return "—"
    return f"{f:.1f}%".replace(".", ",")


def _ym_es(p) -> str:
    """Periodo YYYYMM -> MM-YYYY para etiquetas. NaN-safe."""
    s = str(p).strip()
    if len(s) == 6 and s.isdigit():
        return f"{s[4:]}-{s[:4]}"
    return s if s not in ("", "nan", "None") else "—"


def svg_barras(pares, color="#00AEAC", width=560) -> str:
    """Barras horizontales SVG puro (strings, sin librerías).

    Acepta negativos (eje cero desplazado, negativos en rojo). NaN-safe:
    valores inválidos se omiten; sin datos devuelve aviso, nunca 'nan'.
    """
    items = []
    for lab, val in (pares or []):
        v = fnum(val)
        if v is None:
            continue
        t = str(lab).strip()
        items.append((t[:24] if t not in ("", "nan", "None") else "—", v))
    if not items:
        return '<p class="warn">Gráfico sin datos suficientes para este corte.</p>'
    n = len(items)
    ml, mr, mt, mb = 150, 64, 6, 22
    row, bh = 26, 15
    pw = width - ml - mr
    H = mt + n * row + mb
    vmax = max(0.0, max(v for _, v in items))
    vmin = min(0.0, min(v for _, v in items))
    span = (vmax - vmin) or 1.0

    def _x(v: float) -> float:
        return ml + (v - vmin) / span * pw

    x0 = _x(0.0)
    parts = [f'<svg viewBox="0 0 {width} {H}" width="100%" role="img" xmlns="http://www.w3.org/2000/svg">']
    ticks = sorted({vmin, 0.0, vmax / 2, vmax} if vmin < 0 else {0.0, vmax / 2, vmax})
    for t in ticks:
        tx = _x(t)
        parts.append(f'<line x1="{tx:.1f}" y1="{mt}" x2="{tx:.1f}" y2="{H - mb}" stroke="#D7DEE6" stroke-width="1"/>')
        parts.append(f'<text x="{tx:.1f}" y="{H - 6}" font-size="9" fill="#5A6C7D" text-anchor="middle">{escape(_short_es(t))}</text>')
    for i, (lab, v) in enumerate(items):
        y = mt + i * row
        bx = min(x0, _x(v))
        bw = max(2.0, abs(_x(v) - x0))
        fill = color if v >= 0 else "#C0392B"
        parts.append(f'<text x="{ml - 6}" y="{y + 12}" font-size="9.5" fill="#172139" text-anchor="end">{escape(lab)}</text>')
        parts.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="3" fill="{fill}"/>')
        lx = _x(v) + (6 if v >= 0 else -6)
        anc = "start" if v >= 0 else "end"
        parts.append(f'<text x="{lx:.1f}" y="{y + 12}" font-size="9" fill="#172139" text-anchor="{anc}">{escape(_short_es(v))}</text>')
    parts.append(f'<line x1="{ml}" y1="{H - mb}" x2="{width - mr}" y2="{H - mb}" stroke="#172139" stroke-width="1.2"/>')
    parts.append("</svg>")
    return "".join(parts)


def svg_linea(puntos, color="#108181", width=560, height=230) -> str:
    """Serie temporal SVG pura con ejes y rejilla. NaN-safe: omite inválidos;
    con menos de 2 puntos válidos devuelve aviso."""
    clean = []
    for lab, val in (puntos or []):
        v = fnum(val)
        if v is None:
            continue
        clean.append((str(lab).strip()[:16], v))
    if len(clean) < 2:
        return '<p class="warn">Serie sin datos suficientes para este corte.</p>'
    ml, mr, mt, mb = 48, 12, 10, 30
    pw, ph = width - ml - mr, height - mt - mb
    ys = [v for _, v in clean]
    lo, hi = min(ys), max(ys)
    if hi == lo:
        hi, lo = hi + 1, lo - 1
    pad = (hi - lo) * 0.08
    hi, lo = hi + pad, lo - pad

    def _x(i: int) -> float:
        return ml + (i / (len(clean) - 1)) * pw

    def _y(v: float) -> float:
        return mt + (1 - (v - lo) / (hi - lo)) * ph

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" xmlns="http://www.w3.org/2000/svg">']
    for k in range(5):
        g = lo + (hi - lo) * k / 4
        gy = _y(g)
        parts.append(f'<line x1="{ml}" y1="{gy:.1f}" x2="{width - mr}" y2="{gy:.1f}" stroke="#D7DEE6" stroke-width="1"/>')
        parts.append(f'<text x="{ml - 5}" y="{gy + 3:.1f}" font-size="9" fill="#5A6C7D" text-anchor="end">{escape(_short_es(g))}</text>')
    step = max(1, len(clean) // 8)
    for i, (lab, _v) in enumerate(clean):
        if i % step == 0 or i == len(clean) - 1:
            parts.append(f'<text x="{_x(i):.1f}" y="{height - 8}" font-size="8.5" fill="#5A6C7D" text-anchor="middle">{escape(lab)}</text>')
    pts = " ".join(f"{_x(i):.1f},{_y(v):.1f}" for i, (_, v) in enumerate(clean))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
    for i, (_, v) in enumerate(clean):
        parts.append(f'<circle cx="{_x(i):.1f}" cy="{_y(v):.1f}" r="2.6" fill="{color}"/>')
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{height - mb}" stroke="#172139" stroke-width="1.2"/>')
    parts.append(f'<line x1="{ml}" y1="{height - mb}" x2="{width - mr}" y2="{height - mb}" stroke="#172139" stroke-width="1.2"/>')
    parts.append("</svg>")
    return "".join(parts)


def build_insights(pais, dest, marca, occ, al_serie, r, y1, pcol, vcol) -> list:
    """Motor de insights: reglas deterministas en ES con cifras reales.

    Cada insight cita su fuente. Si falta un CSV, el insight lo dice de forma
    honesta en lugar de inventar cifras. Nunca emite 'nan'."""
    out: list = []
    fecha = txt(r.get("fecha"))
    c_med = f"med_{y1}"
    # 1-2. Mayor crecimiento y mayor caída YoY entre emisores con base > 1000.
    try:
        rows = []
        if not pais.empty and "med_yoy" in pais.columns and c_med in pais.columns:
            for _, _rw in pais.iterrows():
                b = fnum(_rw[c_med])
                y = fnum(_rw["med_yoy"])
                if b is not None and b > 1000 and y is not None:
                    rows.append((txt(_rw["pais"]), b, y))
        if rows:
            up = max(rows, key=lambda t: t[2])
            dn = min(rows, key=lambda t: t[2])
            out.append(f"El emisor con mayor crecimiento YoY hacia Medellín es {up[0]} con {_pct_es(up[2])} (base de {fmt(up[1])} llegadas en {y1}). Fuente: pais_dashboard {y1}.")
            out.append(f"La mayor caída YoY entre emisores con base mayor a 1.000 es {dn[0]} con {_pct_es(dn[2])} (base de {fmt(dn[1])} llegadas en {y1}). Fuente: pais_dashboard {y1}.")
        else:
            out.append(f"Sin datos suficientes de emisores para calcular crecimiento y caída YoY (falta pais_dashboard.csv o columnas esperadas). Fuente: pais_dashboard {y1}.")
    except Exception:
        out.append("No fue posible calcular el crecimiento YoY de emisores en este corte. Fuente: pais_dashboard.")
    # 3. Alertas: share de seguridad > 8% o sentimiento de marca negativo.
    shr = fnum(r.get("llm_share_seguridad"))
    sm = fnum(r.get("llm_sent_marca"))
    if shr is not None and shr > 0.08:
        out.append(f"Alerta: la categoría seguridad concentra el {share(shr)} de las menciones LLM, por encima del umbral del 8%. Fuente: marca_llm (kpis_historico {fecha}).")
    elif shr is not None:
        out.append(f"Sin alerta de seguridad: su share en menciones LLM es {share(shr)}, bajo el umbral del 8%. Fuente: marca_llm (kpis_historico {fecha}).")
    else:
        out.append("Sin datos de share de seguridad LLM en este corte (falta marca_llm.csv). Fuente: marca_llm.")
    if sm is not None and sm < 0:
        out.append(f"Alerta: el sentimiento neto de marca LLM es negativo ({sfmt(sm, 3)}). Fuente: marca_llm (kpis_historico {fecha}).")
    elif sm is not None:
        out.append(f"El sentimiento neto de marca LLM se mantiene en terreno positivo ({sfmt(sm, 3)}). Fuente: marca_llm (kpis_historico {fecha}).")
    else:
        out.append("Sin datos de sentimiento de marca LLM en este corte (falta marca_llm.csv). Fuente: marca_llm.")
    # 4. Tópico LLM dominante con su categoría.
    try:
        if not marca.empty and {"categoria", "n", "share", "top_topico"}.issubset(marca.columns):
            m2 = marca.copy()
            m2["_n"] = [fnum(v) or 0.0 for v in marca["n"].tolist()]
            _tp = m2.sort_values("_n", ascending=False).iloc[0]
            out.append(f"El tópico LLM dominante es «{txt(_tp['top_topico'])}», dentro de la categoría «{txt(_tp['categoria'])}» ({fmt(_tp['n'])} menciones, share {share(_tp['share'])}). Fuente: marca_llm.")
        else:
            out.append("Sin datos de categorías LLM en este corte (falta marca_llm.csv o columnas esperadas). Fuente: marca_llm.")
    except Exception:
        out.append("No fue posible identificar el tópico LLM dominante en este corte. Fuente: marca_llm.")
    # 5. Mejor y peor mes de ocupación hotelera.
    try:
        _occ = occ
        if pcol and vcol and _occ is not None and not _occ.empty and pcol in _occ.columns and vcol in _occ.columns:
            _vv = [(row[pcol], fnum(row[vcol])) for _, row in _occ.iterrows()]
            _vv = [(p, v) for p, v in _vv if v is not None]
            if _vv:
                _hi = max(_vv, key=lambda t: t[1])
                _lo = min(_vv, key=lambda t: t[1])
                _pmax = str(max(str(p) for p, _v in _vv))
                out.append(f"Ocupación hotelera en Medellín (baseline histórico {_pmax}; vs baseline 2023): el mejor mes fue {_ym_es(_hi[0])} con {_p1_es(_hi[1])} y el más bajo fue {_ym_es(_lo[0])} con {_p1_es(_lo[1])}. Fuente: medata_ocupacion_med.")
            else:
                out.append("Serie de ocupación sin valores válidos en este corte. Fuente: medata_ocupacion_med.")
        else:
            out.append("Serie de ocupación no disponible en este corte (falta medata_ocupacion_med.csv). Fuente: medata_ocupacion_med.")
    except Exception:
        out.append("No fue posible calcular el mejor y peor mes de ocupación en este corte. Fuente: medata_ocupacion_med.")
    # 6. Top destino de Colombia y su YoY.
    try:
        if not dest.empty and "ciudad" in dest.columns:
            _d0 = dest.iloc[0]
            _ycol = f"llegadas_{y1}"
            _dval = fmt(_d0[_ycol]) if _ycol in dest.columns else "—"
            _dyoy = _pct_es(_d0["yoy"]) if "yoy" in dest.columns else "—"
            out.append(f"El top destino de Colombia es {txt(_d0['ciudad'])} con {_dval} llegadas en {y1} ({_dyoy} YoY). Fuente: destinos_dashboard {y1}.")
        else:
            out.append("Sin datos de destinos en este corte (falta destinos_dashboard.csv). Fuente: destinos_dashboard.")
    except Exception:
        out.append("No fue posible identificar el top destino en este corte. Fuente: destinos_dashboard.")
    # 7. Ventana móvil H1-2026 (abr–jun 2026): insight principal, nunca baseline.
    try:
        _u3t, _u3y, _u3v = fnum(r.get("med_ult3m_total")), fnum(r.get("med_ult3m_yoy")), txt(r.get("med_ventana"))
        if _u3t is not None and _u3v != "—":
            out.append(f"En la ventana {_u3v} (H1-2026) Medellín recibió {fmt(_u3t)} llegadas ({_pct_es(_u3y)} YoY). Fuente: pais_dashboard ult3m.")
        else:
            out.append("Sin datos de ventana móvil ult3m en este corte. Fuente: pais_dashboard ult3m.")
    except Exception:
        out.append("No fue posible calcular la ventana móvil ult3m en este corte. Fuente: pais_dashboard ult3m.")
    # 8. Gasto DANE: principal si es II-2026; si el trimestre es viejo se etiqueta.
    try:
        _gt, _gv = txt(r.get("gasto_trimestre")), fnum(r.get("gasto_prom_dia_cop"))
        if _gt != "—" and _gv is not None:
            if es_trim_actual(_gt):
                out.append(f"El gasto promedio diario (DANE, {_gt}) fue de ${fmt(_gv)} COP. Fuente: dane_egit_gasto_dia {_gt}.")
            else:
                out.append(f"Gasto promedio diario de ${fmt(_gv)} COP (baseline histórico {_gt}). Fuente: dane_egit_gasto_dia {_gt}.")
        else:
            out.append("Sin datos de gasto diario en este corte (falta dane_egit_gasto_dia). Fuente: dane_egit_gasto_dia.")
    except Exception:
        out.append("No fue posible identificar el gasto diario en este corte. Fuente: dane_egit_gasto_dia.")
    import re as _re
    return [s for s in out if str(s).strip() and not _re.search(r"(?<![\wáéíóú])nan(?![\w])", str(s).lower())]


def run() -> Path:
    hist = pd.read_csv(PROC / "kpis_historico.csv") if (PROC / "kpis_historico.csv").exists() else pd.DataFrame()
    r = hist.iloc[-1].to_dict() if not hist.empty else {}
    fecha = str(r.get("fecha", date.today().isoformat()))

    pais = pd.read_csv(PROC / "pais_dashboard.csv") if (PROC / "pais_dashboard.csv").exists() else pd.DataFrame()
    dest = pd.read_csv(PROC / "destinos_dashboard.csv") if (PROC / "destinos_dashboard.csv").exists() else pd.DataFrame()
    marca = pd.read_csv(PROC / "marca_llm.csv") if (PROC / "marca_llm.csv").exists() else pd.DataFrame()
    y1 = str(pais["ano_ref"].iloc[0]) if not pais.empty and "ano_ref" in pais.columns else "2025"
    c_med, c_nac = f"med_{y1}", f"nac_{y1}"

    alerts = latest_raw("alerts_rss")
    occ = latest_raw("medata_ocupacion_med")
    al_serie = pd.read_csv(PROC / "desglose_alertas_serie.csv") if (PROC / "desglose_alertas_serie.csv").exists() else pd.DataFrame()
    crm_p = RAW / "manual" / "crm.xlsx"
    crm = pd.read_excel(crm_p, sheet_name=0) if crm_p.exists() else pd.DataFrame()

    top_pais = pais.head(10) if not pais.empty else pd.DataFrame()
    top_dest = dest.head(12) if not dest.empty else pd.DataFrame()
    top_men = alerts.head(20) if not alerts.empty else pd.DataFrame()
    last_occ = occ.tail(12) if not occ.empty else pd.DataFrame()

    pcol = next((c for c in occ.columns if "periodo" in c.lower()), None) if not occ.empty else None
    vcol = next((c for c in occ.columns if "valor" in c.lower()), None) if not occ.empty else None
    ventana3m = txt(r.get("med_ventana")) if txt(r.get("med_ventana")) != "—" else "abr-2026 a jun-2026"
    gasto_tri = txt(r.get("gasto_trimestre"))
    mes_corte = mes_corte_es(fecha)
    occ_per_max = txt(r.get("occ_med_periodo"))
    tar_per = txt(r.get("tarifa_med_periodo"))
    mde_per = txt(r.get("mde_hist_periodo"))
    occ_badge_per = occ_per_max
    try:
        if pcol and not occ.empty and pcol in occ.columns:
            _pers = sorted(str(v).strip() for v in occ[pcol].tolist() if str(v).strip() not in ("", "nan", "None"))
            if _pers:
                occ_badge_per = _pers[-1]
    except Exception:
        occ_badge_per = occ_per_max
    ult3m = pd.read_csv(PROC / "ult3m_pais.csv") if (PROC / "ult3m_pais.csv").exists() else pd.DataFrame()
    top_ult3m = ult3m.head(10) if not ult3m.empty else pd.DataFrame()

    # --- 1. Reuniones (MICE) ---
    _der = fnum(r.get("derrama_mice"))
    _noc = fnum(r.get("noches_mice"))
    if _der is not None and _noc:
        derr_noche = f"USD {fmt(_der / _noc)}"
    else:
        derr_noche = "—"
    s_mice = '<div class="kpis">' + "".join([
        kpi(f"Win rate RFP (corte {fecha[:4]})", share(r.get("win_rate"))),
        kpi(f"Noches MICE (corte {fecha[:4]})", fmt(r.get("noches_mice"))),
        kpi(f"Derrama estimada (corte {fecha[:4]})", f"USD {fmt(r.get('derrama_mice'))}"),
        kpi(f"Derrama por noche (corte {fecha[:4]})", derr_noche),
        kpi(f"Pipeline ponderado (corte {fecha[:4]})", f"USD {fmt(r.get('pipeline_ponderado'))}"),
        kpi("Uplift feria (pp)", fmt(r.get("uplift_feria_pp"))),
        kpi_hist("Tarifa prom. Medellín", f"${fmt(r.get('tarifa_med_ult'))} COP ({tar_per})", tar_per),
        kpi("PITS (puntos info)", fmt(r.get("pits_filas"))),
        kpi_hist("Top emisor histórico MDE", txt(r.get("mde_top_emisor_hist")), mde_per),
        kpi_hist("Share top3 histórico MDE", share(r.get("mde_top3_share_hist")), mde_per),
        kpi_hist("Periodo serie MDE", mde_per, mde_per),
        kpi(f"Alerta semanal máx. (corte {fecha[:4]})", fmt(r.get("alertas_sem_max"))),
    ]) + "</div>"
    t_occ = ""
    if pcol and vcol and not last_occ.empty:
        t_occ = f"<h3>Ocupación hotelera mensual Medellín (%) — contexto secundario {badge_hist(occ_badge_per)}</h3>" + table(
            ["Periodo", "Ocupación %"],
            [[str(a), round(float(b), 1)] for a, b in zip(last_occ[pcol].tolist(), last_occ[vcol].tolist(), strict=True)],
        )
    t_crm = ""
    if not crm.empty:
        t_crm = "<h3>Pipeline RFP (CRM interno)</h3>" + table(
            list(map(str, crm.columns))[:6],
            crm.iloc[:20, :6].values.tolist(),
        )

    # --- 2. Vacacional ---
    s_vac = '<div class="kpis">' + "".join([
        kpi("Extranjeros no residentes (acum.)", fmt(r.get("llegadas_medellin_nr"))),
        kpi("Top emisor", txt(r.get("top1_emisor"))),
        kpi("Share top5 emisores", share(r.get("share_top5"))),
        kpi("Pax llegadas MDE (acum.)", fmt(r.get("pax_llegadas_mde"))),
        kpi("Pax salidas MDE (acum.)", fmt(r.get("pax_salidas_mde"))),
        kpi("Pax Aerocivil total", fmt(r.get("pax_aerocivil_total"))),
        (kpi(f"Gasto prom/día DANE ({gasto_tri})", f"${fmt(r.get('gasto_prom_dia_cop'))} COP")
         if es_trim_actual(gasto_tri)
         else kpi_hist("Gasto prom/día DANE", f"${fmt(r.get('gasto_prom_dia_cop'))} COP ({gasto_tri})", gasto_tri)),
        kpi_hist("Ocupación Medellín", f"{fmt(r.get('occ_med_ult'))}% ({occ_per_max})", occ_badge_per),
        kpi_hist("Ocupación máx. 12m", f"{fmt(r.get('occ_med_max12'))}%", occ_badge_per),
        kpi(f"Llegadas Medellín ult3m H1-2026 ({ventana3m})", f"{fmt(r.get('med_ult3m_total'))} ({pct(r.get('med_ult3m_yoy'))} YoY)"),
        kpi("Ventana 3m", txt(r.get("med_ventana"))),
        kpi(f"Entradas nacionalidad ult3m ({txt(r.get('entradas_nacionalidad_ventana'))})", f"{fmt(r.get('entradas_nacionalidad_ult3m'))} ({pct(r.get('entradas_nacionalidad_ult3m_yoy'))})"),
        kpi("Ventana nacionalidad", txt(r.get("entradas_nacionalidad_ventana"))),
        kpi(f"Aéreo MDE EOH ult3m ({txt(r.get('aereo_mde_eoh_ventana'))})", f"{fmt(r.get('aereo_mde_eoh_ult3m'))} ({pct(r.get('aereo_mde_eoh_ult3m_yoy'))})"),
        kpi("Ventana aérea", txt(r.get("aereo_mde_eoh_ventana"))),
        kpi("Mujeres entradas (%)", share(r.get("genero_entradas_fem"))),
        kpi("Carga MDE (kg)", fmt(r.get("carga_ult_kg"))),
        kpi("DANE EGIT filas", f"{fmt(r.get('dane_egit_filas'))} (ok={txt(r.get('dane_egit_ok'))})"),
        kpi("DANE ENH filas", f"{fmt(r.get('dane_enh_filas'))} (ok={txt(r.get('dane_enh_ok'))})"),
    ]) + "</div>"
    if es_trim_actual(gasto_tri):
        g_gasto = (f'<p class="bul">Gasto II-2026 (DANE): ${escape(fmt(r.get("gasto_prom_dia_cop")))} COP promedio/día en {escape(gasto_tri)}. Fuente: dane_egit_gasto_dia.</p>')
    else:
        g_gasto = (f'<p class="warn">Gasto diario {badge_hist(gasto_tri)}: ${escape(fmt(r.get("gasto_prom_dia_cop")))} COP en {escape(gasto_tri)}. Fuente: dane_egit_gasto_dia.</p>')
    _llm_bal = "—"
    if not marca.empty and {"pos", "neg"}.issubset(marca.columns):
        _pp = [fnum(v) or 0.0 for v in marca["pos"].tolist()]
        _nn = [fnum(v) or 0.0 for v in marca["neg"].tolist()]
        _llm_bal = f"{int(sum(_pp) - sum(_nn)):+d}"
    s_mar = '<div class="kpis">' + "".join([
        kpi(f"Menciones 7d ({mes_corte})", fmt(r.get("menciones"))),
        kpi("Sentimiento neto", sfmt(r.get("sentimiento_neto"))),
        kpi("Share Medellín", share(r.get("share_medellin"))),
        kpi(f"Vol. GDELT 7d ({mes_corte})", fmt(r.get("gdelt_vol_7d"))),
        kpi(f"Menciones prensa 7d ({mes_corte})", fmt(r.get("menciones_prensa_7d"))),
        kpi(f"Interés Wikipedia 30d ({mes_corte})", fmt(r.get("interes_wiki_30d"))),
        kpi("Balance LLM (pos−neg)", _llm_bal),
        kpi("Menciones clasificadas LLM", fmt(r.get("llm_menciones_clasif"))),
        kpi("Top categoría LLM", txt(r.get("llm_top_categoria"))),
        kpi("Share top categoría", share(r.get("llm_top_cat_share"))),
        kpi("Sent. neto marca LLM", sfmt(r.get("llm_sent_marca"), 3)),
        kpi("Sent. neto global LLM", sfmt(r.get("llm_sent_net"), 3)),
        kpi("Share seguridad LLM", share(r.get("llm_share_seguridad"))),
        kpi("Top tópico LLM", txt(r.get("llm_top_topico"))),
    ]) + "</div>"
    if not marca.empty and {"categoria", "n", "share", "sent_net", "top_topico"}.issubset(marca.columns):
        t_mar = "<h3>Marca por categoría (clasificación LLM)</h3>" + table(
            ["Categoría", "N", "Share", "Pos", "Neu", "Neg", "Sent. neto", "Top tópico"],
            [[str(a), fmt(b), share(c), fmt(d), fmt(e), fmt(f), f"{0.0 if _na(g) else float(g):+.3f}", str(h)]
             for a, b, c, d, e, f, g, h in zip(
                marca["categoria"].tolist(), marca["n"].tolist(), marca["share"].tolist(),
                marca["pos"].tolist(), marca["neu"].tolist(), marca["neg"].tolist(),
                marca["sent_net"].tolist(), marca["top_topico"].tolist(), strict=True)],
        )
    else:
        t_mar = ('<p class="warn">Clasificación LLM no disponible para este corte '
                 "(falta marca_llm.csv o columnas esperadas): las tarjetas LLM muestran — .</p>")
    t_men = ""
    if not top_men.empty and {"fecha", "titulo"}.issubset(top_men.columns):
        t_men = f"<h3>Últimas menciones {escape(mes_corte)} (Google News + Reddit, sin login)</h3>" + table(
            ["Fecha", "Titular"],
            [[str(a)[:16], str(b)] for a, b in zip(top_men["fecha"].tolist(), top_men["titulo"].tolist(), strict=True)],
        )

    # --- 4. Emisores ---
    _t1yoy = _t1sh = _t1nac = "—"
    if not top_pais.empty:
        _row0 = top_pais.iloc[0]
        _t1yoy = pct(_row0["med_yoy"]) if "med_yoy" in top_pais.columns else "—"
        _t1sh = share(_row0["share_med"]) if "share_med" in top_pais.columns else "—"
        _t1nac = fmt(_row0[c_nac]) if c_nac in top_pais.columns else "—"
    s_emi = '<div class="kpis">' + "".join([
        kpi(f"Emisor top1 ({y1})", f"{txt(r.get('emisor_top1'))} ({fmt(r.get('emisor_top1_med'))})"),
        kpi(f"YoY top1 Medellín ({y1})", _t1yoy),
        kpi(f"Share top1 Medellín ({y1})", _t1sh),
        kpi(f"Top1 Colombia total ({y1})", _t1nac),
        kpi(f"Emisor top2 ({y1})", f"{txt(r.get('emisor_top2'))} ({fmt(r.get('emisor_top2_med'))})"),
        kpi(f"Emisor top3 ({y1})", f"{txt(r.get('emisor_top3'))} ({fmt(r.get('emisor_top3_med'))})"),
        kpi(f"Share top5 emisores ({y1})", share(r.get("emisor_top5_share"))),
        kpi(f"Mayor crecimiento ({y1})", f"{txt(r.get('emisor_crec_top'))} ({pct(r.get('emisor_crec_top_yoy'))} YoY)"),
        kpi(f"Share top5 serie ({y1})", share(r.get("share_top5"))),
    ]) + "</div>"
    t_pais = ""
    if not top_pais.empty:
        t_pais = f'<p class="bul">Año de referencia {escape(y1)} · {len(pais)} países · top emisor {escape(str(top_pais.iloc[0]["pais"]))}</p>'
        t_pais += "<h3>Ranking por país emisor (top 10)</h3>" + table(
            ["País", f"Medellín {y1}", "YoY Med", "Share Med", f"Colombia {y1}"],
            [[str(a), fmt(b), pct(c), share(d), fmt(e)]
             for a, b, c, d, e in zip(
                top_pais["pais"].tolist(),
                top_pais[c_med].tolist() if c_med in top_pais.columns else ["—"] * len(top_pais),
                top_pais["med_yoy"].tolist() if "med_yoy" in top_pais.columns else ["—"] * len(top_pais),
                top_pais["share_med"].tolist() if "share_med" in top_pais.columns else ["—"] * len(top_pais),
                top_pais[c_nac].tolist() if c_nac in top_pais.columns else ["—"] * len(top_pais), strict=True)],
        )

    # --- 5. Destinos + Outbound ---
    _dest_ytd = "—"
    if not top_dest.empty and "llegadas_2026_ytd" in top_dest.columns:
        _dest_ytd = fmt(top_dest.iloc[0]["llegadas_2026_ytd"])
    _out_serie = _out_serie_yoy = "—"
    if not pais.empty and txt(r.get("salidas_top_dest")) != "—":
        _pm = pais[pais["pais"] == txt(r.get("salidas_top_dest"))]
        if not _pm.empty:
            _pm0 = _pm.iloc[0]
            _out_serie = fmt(_pm0["sal_2025"]) if "sal_2025" in pais.columns else "—"
            _out_serie_yoy = pct(_pm0["sal_yoy"]) if "sal_yoy" in pais.columns else "—"
    s_des = '<div class="kpis">' + "".join([
        kpi(f"Top destino Colombia ({y1})", f"{txt(r.get('destino_top'))} ({fmt(r.get('destino_top_valor'))})"),
        kpi("Top destino YTD 2026", _dest_ytd),
        kpi(f"Share Medellín ({y1})", share(r.get("destino_med_share"))),
        kpi(f"Destino mayor crec. ({y1})", f"{txt(r.get('destino_crec_top'))} ({pct(r.get('destino_crec_top_yoy'))} YoY)"),
        kpi(f"Salidas colombianos total ({y1})", fmt(r.get("salidas_total"))),
        kpi(f"Top destino outbound ({y1})", f"{txt(r.get('salidas_top_dest'))} ({fmt(r.get('salidas_top_valor'))})"),
        kpi(f"YoY top outbound ({y1})", pct(r.get("salidas_top_yoy"))),
        kpi("Top outbound serie 2025", f"{_out_serie} ({_out_serie_yoy} YoY)"),
        kpi(f"Salidas por destino ult3m ({txt(r.get('salidas_destino_ventana'))})", f"{fmt(r.get('salidas_destino_ult3m'))} ({pct(r.get('salidas_destino_ult3m_yoy'))})"),
        kpi("Ventana salidas", txt(r.get("salidas_destino_ventana"))),
        kpi("Mujeres salidas (%)", share(r.get("genero_salidas_fem"))),
        kpi(f"Salidas COL total serie ({y1})", fmt(r.get("salidas_col_total"))),
    ]) + "</div>"
    t_dest = ""
    if not top_dest.empty:
        t_dest = f"<h3>Destinos Colombia — ranking {escape(y1)}</h3>" + table(
            ["Destino", f"Llegadas {y1}", "Share", "YoY"],
            [[str(a), fmt(b), share(c), pct(d)]
             for a, b, c, d in zip(
                top_dest["ciudad"].tolist(),
                top_dest[f"llegadas_{y1}"].tolist() if f"llegadas_{y1}" in top_dest.columns else ["—"] * len(top_dest),
                top_dest["share"].tolist() if "share" in top_dest.columns else ["—"] * len(top_dest),
                top_dest["yoy"].tolist() if "yoy" in top_dest.columns else ["—"] * len(top_dest), strict=True)],
        )

    # --- 6. Territorio ---
    _rm = fnum(r.get("rnt_med_total"))
    _ra = fnum(r.get("rnt_ant_total"))
    _rnt_tot = fmt(_rm + _ra) if _rm is not None and _ra is not None else "—"
    _hu = fnum(r.get("hurtos_med_ult"))
    _ho = fnum(r.get("homicidios_med_ult"))
    _del = fmt(_hu + _ho) if _hu is not None and _ho is not None else "—"
    s_ter = '<div class="kpis">' + "".join([
        kpi("RNT Medellín", fmt(r.get("rnt_med_total"))),
        kpi("RNT Antioquia", fmt(r.get("rnt_ant_total"))),
        kpi("RNT total Med+Ant", _rnt_tot),
        kpi(f"Hurtos Medellín (últ., {mes_corte})", fmt(r.get("hurtos_med_ult"))),
        kpi(f"Homicidios Medellín (últ., {mes_corte})", fmt(r.get("homicidios_med_ult"))),
        kpi(f"Delitos hurtos+hom. ({mes_corte})", _del),
        kpi(f"Lluvia Medellín mm ({mes_corte})", fmt(r.get("lluvia_med_mm"))),
        kpi(f"PM2.5 Medellín ({mes_corte})", fmt(r.get("pm25_med"))),
        kpi(f"Pax terminales ({mes_corte})", fmt(r.get("pax_terminal_mes"))),
        kpi(f"Pax Metro ({mes_corte})", fmt(r.get("pax_metro_mes"))),
        kpi(f"TRM hoy ({fecha})", f"${fmt(r.get('trm_hoy'))} COP"),
        kpi(f"Festivos CO ({fecha[:4]})", fmt(r.get("festivos_co_ano"))),
    ]) + "</div>"

    # --- 7. Benchmark EU ---
    s_eu = '<div class="kpis">' + "".join([
        kpi("Noches EU total", fmt(r.get("noches_eu_total"))),
        kpi("Camas EU total", fmt(r.get("camas_eu_total"))),
        kpi("Demanda EU (viajes)", fmt(r.get("demanda_eu_viajes"))),
        kpi("Pax EU España", fmt(r.get("pax_eu_es"))),
        kpi("Gasto emisor top (USD)", f"USD {fmt(r.get('gasto_emisor_top_usd'))}"),
        kpi("Gasto emisor CO (USD)", f"USD {fmt(r.get('gasto_emisor_co_usd'))}"),
    ]) + "</div>"

    # --- 8. Alojamiento (EMA) + Agenda + Aéreo en vivo (P1: S2/S3/S4) ---
    # Un try/except por fuente: si falta el CSV, la subsección muestra nota
    # SKIP honesta sin romper el build (patrón defensivo del archivo).
    _p1k: list = []
    t_ema = ""
    try:
        _ema_p = PROC / "desglose_ema.csv"
        if _ema_p.exists():
            _ema = pd.read_csv(_ema_p)
            _per = "2026-08"
            if not _ema.empty and "periodo" in _ema.columns and (_ema["periodo"].astype(str) == _per).any():
                _er = _ema[_ema["periodo"].astype(str) == _per].iloc[0].to_dict()

                def _ema_var(col) -> str:
                    v = fnum(_er.get(col))
                    return f"{v:+.1f}%".replace(".", ",") if v is not None else "—"

                _ing = _ema_var("Ingresos reales var anual — Total nacional")
                _peo = _ema_var("Personal ocupado var anual — Total nacional")
                _sal = _ema_var("Salarios reales var anual — Total nacional")
                _acu = _ema_var("Ingresos reales var año corrido — Total nacional")
                _ocn = _p1_es(fnum(_er.get("Ocupación — Total nacional")))
                _p1k += [
                    kpi("Ingresos reales EMA var anual (ago-2026, nac.)", _ing),
                    kpi("Personal ocupado EMA var anual (ago-2026, nac.)", _peo),
                    kpi("Salarios reales EMA var anual (ago-2026, nac.)", _sal),
                    kpi("Ingresos reales EMA año corrido (ene–ago 2026, nac.)", _acu),
                    kpi("Ocupación EMA (ago-2026, nac.)", _ocn),
                ]
                t_ema = ("<h3>Alojamiento EMA DANE — var anual ago-2026 (nacional vs Antioquia)</h3>" + table(
                    ["Indicador (ago-2026)", "Total nacional", "Antioquia"],
                    [
                        ["Ingresos reales var anual", _ing, _ema_var("Ingresos reales var anual — Antioquia")],
                        ["Personal ocupado var anual", _peo, _ema_var("Personal ocupado var anual — Antioquia")],
                        ["Salarios reales var anual", _sal, _ema_var("Salarios reales var anual — Antioquia")],
                        ["Ocupación", _ocn, _p1_es(fnum(_er.get("Ocupación — Antioquia")))],
                    ],
                ) + '<p class="src">Fuente: DANE EMA anex-EMA-ago2026.xlsx (actualizado 16-oct-2026) · PROC/desglose_ema.csv.</p>')
            else:
                t_ema = '<p class="warn">EMA sin periodo 2026-08 en este corte (desglose_ema.csv sin la fila esperada): tarjetas EMA omitidas.</p>'
        else:
            t_ema = '<p class="warn">EMA no disponible en este corte (falta desglose_ema.csv): tarjetas EMA omitidas.</p>'
    except Exception:
        t_ema = '<p class="warn">EMA no disponible en este corte (desglose_ema.csv ilegible): tarjetas EMA omitidas.</p>'
    t_ev = ""
    try:
        _ev_p = PROC / "desglose_eventos.csv"
        if _ev_p.exists():
            _ev = pd.read_csv(_ev_p)
            if not _ev.empty and {"fecha", "nombre"}.issubset(_ev.columns):
                _ev10 = _ev.head(10)
                _evcols = ["fecha", "nombre", "recinto", "ciudad", "categoria"]
                t_ev = ("<h3>Agenda — próximos eventos (Ticketmaster)</h3>" + table(
                    ["Fecha", "Evento", "Recinto", "Ciudad", "Categoría"],
                    [[txt(rw[c]) if c in _ev10.columns else "—" for c in _evcols] for _, rw in _ev10.iterrows()],
                ) + '<p class="src">Fuente: Ticketmaster Discovery API (radio Medellín) · PROC/desglose_eventos.csv (próximos 10).</p>')
            else:
                t_ev = '<p class="warn">Agenda no disponible en este corte (desglose_eventos.csv sin columnas esperadas).</p>'
        else:
            t_ev = '<p class="warn">Agenda no disponible en este corte (falta desglose_eventos.csv; Ticketmaster SKIP sin key): sin próximos eventos.</p>'
    except Exception:
        t_ev = '<p class="warn">Agenda no disponible en este corte (desglose_eventos.csv ilegible).</p>'
    t_sky = ""
    try:
        _sky = latest_raw("opensky_states")
        if not _sky.empty and {"vuelo", "pais"}.issubset(_sky.columns):
            _srows = []
            for _, _rw in _sky.iterrows():
                _g = str(_rw["en_tierra"]).lower() if "en_tierra" in _sky.columns else "false"
                if _g not in ("true", "1", "t"):
                    _srows.append([txt(_rw["vuelo"]), txt(_rw["pais"])])
            if not _srows:
                _srows = [[txt(_rw["vuelo"]), txt(_rw["pais"])] for _, _rw in _sky.iterrows()]
            _snap = txt(_sky["periodo"].iloc[0]) if "periodo" in _sky.columns else fecha
            _p1k.append(kpi(f"Aeronaves en vuelo MDE/EOH (snapshot {_snap})", fmt(len(_srows))))
            t_sky = ("<h3>Aéreo en vivo — snapshot MDE/EOH (OpenSky, top 10 en vuelo)</h3>" + table(
                ["Vuelo", "País"],
                _srows[:10],
            ) + '<p class="src">Fuente: OpenSky Network states/all (bbox MDE/EOH) · snapshot en vivo.</p>')
        else:
            t_sky = '<p class="warn">Aéreo en vivo no disponible en este corte (falta opensky_states.csv): sin snapshot MDE/EOH.</p>'
    except Exception:
        t_sky = '<p class="warn">Aéreo en vivo no disponible en este corte (opensky_states.csv ilegible).</p>'
    s_p1 = '<div class="kpis">' + "".join(_p1k) + "</div>" if _p1k else ""

    # --- Gráficos SVG inline (S2) + motor de insights (S3) ---
    if not top_pais.empty and c_med in top_pais.columns:
        g_emi = (f"<h3>Top 10 emisores hacia Medellín (llegadas {escape(y1)})</h3>"
                 + svg_barras([(rw["pais"], rw[c_med]) for _, rw in top_pais.iterrows()]))
    else:
        g_emi = '<p class="warn">Gráfico de emisores no disponible en este corte (falta pais_dashboard.csv).</p>'
    if not top_dest.empty and f"llegadas_{y1}" in top_dest.columns:
        g_dest = (f"<h3>Top 12 destinos de Colombia (llegadas {escape(y1)})</h3>"
                  + svg_barras([(rw["ciudad"], rw[f"llegadas_{y1}"]) for _, rw in top_dest.iterrows()]))
    else:
        g_dest = '<p class="warn">Gráfico de destinos no disponible en este corte (falta destinos_dashboard.csv).</p>'
    if pcol and vcol and not last_occ.empty and pcol in last_occ.columns and vcol in last_occ.columns:
        _occ_s = last_occ.sort_values(pcol)
        g_occ = (f"<h3>Ocupación hotelera mensual Medellín (%) — serie {badge_hist(occ_badge_per)}</h3>"
                 + svg_linea([(_ym_es(a), b) for a, b in zip(_occ_s[pcol].tolist(), _occ_s[vcol].tolist(), strict=True)], color="#108181"))
    else:
        g_occ = '<p class="warn">Serie de ocupación no disponible en este corte (falta medata_ocupacion_med.csv).</p>'
    if not marca.empty and {"categoria", "sent_net"}.issubset(marca.columns):
        g_sent = ("<h3>Sentimiento neto por categoría (clasificación LLM)</h3>"
                  + svg_barras([(rw["categoria"], rw["sent_net"]) for _, rw in marca.iterrows()]))
    else:
        g_sent = '<p class="warn">Gráfico de sentimiento no disponible en este corte (falta marca_llm.csv).</p>'
    if not al_serie.empty and {"fecha", "n"}.issubset(al_serie.columns):
        _al = al_serie.tail(12)
        g_al = (f"<h3>Menciones semanales de alertas (últimas 12 semanas, corte {escape(mes_corte)})</h3>"
                + svg_barras([(rw["fecha"], rw["n"]) for _, rw in _al.iterrows()], color="#E9901E"))
    else:
        g_al = '<p class="warn">Serie de menciones semanales no disponible en este corte (falta desglose_alertas_serie.csv).</p>'
    if not top_ult3m.empty and "med_ult3m" in top_ult3m.columns:
        _v3 = txt(top_ult3m["ventana"].iloc[0]) if "ventana" in top_ult3m.columns else ventana3m
        g_ult3m = (f"<h3>Top 10 emisores ult3m H1-2026 ({escape(_v3)} + YoY)</h3>"
                   + svg_barras([(rw["pais"], rw["med_ult3m"]) for _, rw in top_ult3m.iterrows()])
                   + f"<h3>Detalle ult3m por emisor (H1-2026, {escape(_v3)})</h3>" + table(
                       ["País", f"Llegadas {_v3}", "YoY"],
                       [[str(a), fmt(b), pct(c)]
                        for a, b, c in zip(
                           top_ult3m["pais"].tolist(),
                           top_ult3m["med_ult3m"].tolist(),
                           top_ult3m["med_ult3m_yoy"].tolist() if "med_ult3m_yoy" in top_ult3m.columns else ["—"] * len(top_ult3m), strict=True)]))
    else:
        g_ult3m = '<p class="warn">Gráfico ult3m no disponible en este corte (falta ult3m_pais.csv).</p>'
    insights = build_insights(pais, dest, marca, occ, al_serie, r, y1, pcol, vcol)
    s_ana = "".join(f'<p class="bul">{escape(s)}</p>' for s in insights if str(s).strip())

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
<nav class="toc"><a href="#analisis">Análisis</a><a href="#reuniones">Reuniones</a><a href="#vacacional">Vacacional</a><a href="#marca-llm">Marca+LLM</a><a href="#emisores">Emisores</a><a href="#destinos">Destinos+Outbound</a><a href="#territorio">Territorio</a><a href="#benchmark-eu">Benchmark EU</a><a href="#ema-agenda-aereo">EMA+Agenda+Aéreo</a></nav>
<h2 id="analisis">Análisis</h2><div class="sec">{s_ana}</div>
<h2 id="reuniones">Reuniones (MICE)</h2><div class="sec">{s_mice}{t_occ}{g_occ}{t_crm}</div>
<h2 id="vacacional">Vacacional</h2><div class="sec">{s_vac}{g_gasto}</div>
<h2 id="marca-llm">Marca + LLM</h2><div class="sec">{s_mar}{t_mar}{g_sent}{t_men}{g_al}</div>
<h2 id="emisores">Emisores</h2><div class="sec">{s_emi}{t_pais}{g_emi}{g_ult3m}</div>
<h2 id="destinos">Destinos + Outbound</h2><div class="sec">{s_des}{t_dest}{g_dest}</div>
<h2 id="territorio">Territorio</h2><div class="sec">{s_ter}</div>
<h2 id="benchmark-eu">Benchmark EU</h2><div class="sec">{s_eu}</div>
<h2 id="ema-agenda-aereo">Alojamiento (EMA) + Agenda + Aéreo en vivo</h2><div class="sec">{s_p1}{t_ema}{t_ev}{t_sky}</div>
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
