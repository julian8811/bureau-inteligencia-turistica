#!/usr/bin/env python3
"""Builder SIT emisores -> export/tableros_bureau/sit_emisores_2025_2026.json.

Lee los 5 PDF de perfiles de mercado del SIT Medellin en /tmp/sit/
(Francia, Panama, Republica_Dominicana, Mexico_preview, USA) con pymupdf,
extrae las "Cifras Clave del Periodo" y publica un JSON simple para
tableros-bureau. Solo stdlib + pymupdf + pandas.

Defensivo: PDF ilegible -> ese mercado se omite + nota en "notas",
exit 0, nunca tumba el build. Valores ausentes -> null, jamas inventados.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:  # pragma: no cover - entorno sin pymupdf
    fitz = None

import pandas as pd

BASE = Path(__file__).resolve().parent
SIT_DIR = Path("/tmp/sit")  # noqa: S108 - ruta de entrada fijada por la tarea
OUT = BASE / "tableros_bureau" / "sit_emisores_2025_2026.json"

MERCADOS = [
    ("Francia", "Informe_de_Mercado_SIT_Francia_1ca6621bd2.pdf"),
    ("Panama", "Informe_de_Mercado_SIT_Panama_17a72225d3.pdf"),
    ("Republica Dominicana", "Informe_DOM_SIT_Republica_Dominicana_43d926d3aa.pdf"),
    ("Mexico", "Mexico_preview_430b53dcf4.pdf"),
    ("USA", "Informe_de_mercado_SIT_USA_6c2ff394b8.pdf"),
]


def _desguionar(texto):
    """Normaliza cortes de palabra por guion de fin de linea: 'reg-istradas' -> 'registradas'."""
    return re.sub(r"(\w)-\n(\w)", r"\1\2", texto)


def _num_miles(txt):
    """'439.482' -> 439482 ; '313951' -> 313951."""
    return int(txt.replace(".", "").replace(",", "").strip())


def _num_dec(txt):
    """'92,6' -> 92.6 ; '17.5' -> 17.5."""
    return float(txt.replace(".", "").replace(",", ".").strip()) \
        if "," in txt else float(txt.strip())


def _seccion_cifras(full):
    """Recorta la seccion 'Cifras Clave ...' (hasta la siguiente subseccion 1.x).

    Omite las menciones del indice (TOC): elige la ocurrencia seguida de
    contenido real (bullets o cifras de visitantes)."""
    for m in re.finditer(r"Cifras Clave[^\n]*\n", full):
        ventana = full[m.end():m.end() + 800]
        if re.search(r"•|Visitantes|Total de|llegadas", ventana):
            end = re.search(r"\n1\.[2-9]\b", full[m.end():])
            stop = m.end() + end.start() if end else m.start() + 3500
            return full[m.start():stop]
    return None


def _extraer(mercado, full, sec):
    row = {"mercado": mercado, "periodo": None, "informe_fecha": None,
           "llegadas": None, "yoy_pct": None, "motivo_top": None,
           "motivo_share": None, "estancia_media_dias": None,
           "ticket_prom_cop": None, "anticipacion_dias": None,
           "conectividad_directa_pct": None}
    notas = []
    sec = sec or ""

    m = re.search(r"Fecha (?:del Informe|de An.lisis):\s*(\d{2})/(\d{2})/(\d{4})", full)
    if m:
        row["informe_fecha"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    for pat in (r"en (20\d\d)\s*:",
                r"durante (?:el a.o )?(\d{4})",
                r"diciembre de (\d{4})",
                r"(?:Mercado|mercado)[^\n]{0,40}?(20\d\d)",
                r"\((20\d\d)\)"):
        m = re.search(pat, sec)
        if m:
            row["periodo"] = m.group(1)
            break

    for pat in (r"(\d{1,3}(?:\.\d{3})+)\s*llegadas",
                r"(?:Visitantes|TOTAL|Total)[^:\n]{0,60}:\s*(\d{1,3}(?:\.\d{3})+)",
                r"(\d{1,3}(?:\.\d{3})+)\s*visitantes"):
        m = re.search(pat, sec)
        if m:
            row["llegadas"] = _num_miles(m.group(1))
            break

    m = re.search(r"([+-]\d+[.,]\d+)\s*%\s*frente a\s*\d{4}", sec)
    if m:
        row["yoy_pct"] = _num_dec(m.group(1))

    m = re.search(r"(\d+[.,]\d+)\s*%\s*(Vacaciones[^;\n%]{0,40})", sec)
    if not m:
        m = re.search(r"(Vacaciones[^\n%]{0,40}?)\s*con\s*\n?\s*(\d+[.,]\d+)\s*%", sec)
        if m:
            row["motivo_top"] = re.sub(r"\s+", " ", m.group(1)).strip(" ,;")
            row["motivo_share"] = _num_dec(m.group(2))
    else:
        row["motivo_top"] = re.sub(r"\s+", " ", m.group(2)).strip(" ,;")
        row["motivo_share"] = _num_dec(m.group(1))

    m = re.search(r"[Ee]stancia media:\s*(\d+[.,]?\d*)\s*d.as", sec)
    if m:
        row["estancia_media_dias"] = _num_dec(m.group(1))

    m = re.search(r"[Tt]icket promedio(?: POS)?(?: por transacci.n)?:\s*\$?\s*([\d\.]+)", sec)
    if m:
        row["ticket_prom_cop"] = _num_miles(m.group(1))

    m = re.search(r"[Aa]nticipaci.n (?:de reserva)?:\s*(\d+)\s*d.as", sec)
    if m:
        row["anticipacion_dias"] = int(m.group(1))

    m = re.search(r"[Cc]onectividad (?:directa|real):\s*(\d+[.,]?\d*)\s*%", sec)
    if m:
        row["conectividad_directa_pct"] = _num_dec(m.group(1))

    # Fallback documentado: anticipacion / estadia del radar "Perfil multidimensional"
    # (etiquetas explicitas, fuera de Cifras Clave). Solo si la seccion no trae valor.
    if row["anticipacion_dias"] is None:
        m = re.search(r"Anticipaci.n de Reserva\s*[\(\:]?\s*(\d+)\s*(?:d.as|,|\))", full)
        if m:
            row["anticipacion_dias"] = int(m.group(1))
            notas.append(f"{mercado}: anticipacion_dias={m.group(1)} tomado de Perfil "
                         "multidimensional (fuera de Cifras Clave).")
    if row["estancia_media_dias"] is None:
        m = re.search(r"Estad.a Media\s*[\(\:]?\s*(\d+[.,]?\d*)\s*(?:d.as|,|\))", full)
        if m:
            row["estancia_media_dias"] = _num_dec(m.group(1))
            notas.append(f"{mercado}: estancia_media_dias={m.group(1)} tomado de Perfil "
                         "multidimensional (fuera de Cifras Clave).")

    return row, notas


def _limpio(v):
    """NaN -> None; floats enteros -> int. Garantiza JSON estandar."""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def main():
    notas = []
    filas = []
    if fitz is None:
        notas.append("pymupdf no disponible: ningun mercado extraido.")
    else:
        for mercado, archivo in MERCADOS:
            pdf = SIT_DIR / archivo
            try:
                if not pdf.exists():
                    raise FileNotFoundError(f"no existe {pdf}")
                doc = fitz.open(pdf)
                full = _desguionar("\n".join([str(p.get_text()) for p in doc]))
                doc.close()
                sec = _seccion_cifras(full)
                if not sec:
                    raise ValueError("seccion Cifras Clave no encontrada")
                row, n = _extraer(mercado, full, sec)
                row["archivo"] = archivo
                filas.append(row)
                notas.extend(n)
            except Exception as exc:  # defensivo: omitir mercado, exit 0
                notas.append(f"{mercado}: omitido ({type(exc).__name__}: {exc}).")

    df = pd.DataFrame(filas) if filas else pd.DataFrame()
    notas.append("Francia: la seccion cita 10,8 dias como referente USA, no como "
                 "estancia francesa -> estancia_media_dias=null; sin vuelo directo "
                 "Paris-Medellin -> conectividad_directa_pct=null.")
    notas.append("Republica Dominicana: '31% menos que el mercado mexicano' no es "
                 "variacion interanual -> yoy_pct=null.")

    df = pd.DataFrame(filas) if filas else pd.DataFrame()
    mercados = []
    if not df.empty:
        cols = ["mercado", "archivo", "periodo", "informe_fecha", "llegadas",
                "yoy_pct", "motivo_top", "motivo_share", "estancia_media_dias",
                "ticket_prom_cop", "anticipacion_dias", "conectividad_directa_pct"]
        for vals in df[cols].values.tolist():
            rec = dict(zip(cols, vals, strict=True))
            mercados.append({k: _limpio(rec.get(k)) for k in cols})

    payload = {"id": "bureau-sit",
               "generado": date.today().isoformat(),
               "ventana": "2025",
               "fuente": "ETL Bureau, SIT Medellin perfiles de mercado",
               "mercados": mercados,
               "notas": notas,
               "estado": "ok"}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"mercados={len(mercados)} notas={len(notas)} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
