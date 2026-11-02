"""DANE EMA (Encuesta Mensual de Alojamiento): anexos Excel mensuales.

Patrón verificado 30-oct-2026:
  https://www.dane.gov.co/files/operaciones/EMA/anex-EMA-ago2026.xlsx
Meses en español (ene..dic). Se prueba el mes actual hacia atrás hasta
encontrar un anexo vivo. Mensual, gratis, sin key.

Estructura real: hojas de series con filas Año/Meses y columnas por
región (Total nacional, Bogotá, Cartagena, Central, Caribe, Eje Cafetero,
Antioquia, ...). Valores = variaciones % (V.A/V.A.C/12Meses) o niveles
(ocupación, motivos, tarifas). Se parsea a formato largo con periodo
(AAAA-MM) + fecha_consulta (S6). Nunca tumba el daily.
"""
import re
from datetime import date
from io import BytesIO

import pandas as pd
import requests

from .base import UA, out_dir, save_or_carry

MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]
BASE_URL = "https://www.dane.gov.co/files/operaciones/EMA"

COLUMNS = ["periodo", "indicador", "valor", "unidad",
           "fuente_url", "hoja", "fecha_consulta"]

# serie corta por prefijo de hoja
SERIES = [
    ("1.", "Ingresos reales"),
    ("2.", "Personal ocupado"),
    ("3.", "Salarios reales"),
    ("4.", "Ocupación"),
    ("5.", "Motivo de viaje"),
    ("6.", "Tarifas alojamiento"),
    ("7.", "Oferta y demanda"),
    ("8.", "Índice EMA"),
]


def _serie(sheet: str) -> tuple[str, str]:
    base = next((s for p, s in SERIES if sheet.startswith(p)), sheet.strip())
    low = sheet.lower()
    if "v.a.c" in low or "año corrido" in low:
        return f"{base} var año corrido", "pct"
    if "12mese" in low or "12 mese" in low:
        return f"{base} var 12 meses", "pct"
    if "v.a" in low or "anual" in low:
        return f"{base} var anual", "pct"
    if "ocupaci" in low or "motivo" in low or "porc" in low:
        return base, "pct"
    return base, "indice"


def candidate_urls(lookback_m: int = 8) -> list[str]:
    """anex-EMA-{mes}{anio}.xlsx del mes actual hacia atrás."""
    urls, y, m = [], date.today().year, date.today().month
    for _ in range(lookback_m):
        urls.append(f"{BASE_URL}/anex-EMA-{MESES[m - 1]}{y}.xlsx")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return urls


def _es_anio(v: str) -> str:
    mt = re.match(r"^\s*(19|20)\d{2}\s*p?\s*$", str(v), re.IGNORECASE)
    return mt.group(0).strip() if mt else ""


def _mes_num(v: str) -> int:
    s = str(v).strip().lower()
    for i,abbr in enumerate(MESES, start=1):
        if s.startswith(abbr):
            return i
    return 0


def parse_ema(content: bytes, url: str) -> pd.DataFrame:
    """Hojas EMA (Año/Meses x regiones) -> largo [periodo, indicador, ...]."""
    recs: list[dict] = []
    hoy = date.today().isoformat()
    try:
        x = pd.ExcelFile(BytesIO(content))
    except Exception as e:
        print(f"[ema][WARN] xlsx ilegible ({e})")
        return pd.DataFrame({c: [] for c in COLUMNS})
    for sheet in x.sheet_names:
        if sheet.strip().lower() in ("índice", "indice"):
            continue
        try:
            raw = pd.read_excel(x, sheet_name=sheet, header=None)
        except Exception as e:
            print(f"[ema][WARN] hoja {sheet}: {e}")
            continue
        # fila de columnas: col0 ~= "Año" y col1 ~= "Meses"
        hi = None
        for i in range(min(len(raw), 20)):
            c0, c1 = str(raw.iat[i, 0]).strip().lower(), str(raw.iat[i, 1]).strip().lower()
            if c0.startswith("año") and c1.startswith("mese"):
                hi = i
                break
        if hi is None:
            continue
        regiones = [str(v).strip() for v in raw.iloc[hi, 2:].tolist()]
        serie, unidad = _serie(sheet)
        anio = ""
        for j in range(hi + 1, len(raw)):
            a = _es_anio(raw.iat[j, 0])
            if a:
                anio = re.sub(r"[^0-9]", "", a)[:4]
            mes = _mes_num(raw.iat[j, 1])
            if not anio or not mes:
                continue
            periodo = f"{anio}-{mes:02d}"
            for k, region in enumerate(regiones):
                if not region or region.lower() == "nan":
                    continue
                try:
                    val = float(str(raw.iat[j, k + 2]).replace(",", ""))
                except (ValueError, TypeError):
                    continue
                # NaN check
                if val != val:
                    continue
                recs.append({"periodo": periodo,
                             "indicador": f"{serie} — {region}",
                             "valor": round(val, 4), "unidad": unidad,
                             "fuente_url": url, "hoja": sheet,
                             "fecha_consulta": hoy})
    return pd.DataFrame(recs).reindex(columns=COLUMNS)


def run() -> bool:
    try:
        for u in candidate_urls():
            try:
                r = requests.get(u, headers=UA, timeout=40)
            except Exception as e:
                print(f"[ema][WARN] {u}: {e}")
                continue
            if r.status_code == 200 and len(r.content) > 50000:
                (out_dir() / "dane_ema.xlsx").write_bytes(r.content)
                df = parse_ema(r.content, u)
                save_or_carry(df, "dane_ema", COLUMNS)
                print(f"[ema] OK <- {u} ({len(df)} filas)")
                return True
        print("[ema][SKIP] ningún anexo vivo en lookback")
        return False
    except Exception as e:
        print(f"[ema][SKIP] {e}")
        return False


if __name__ == "__main__":
    run()
