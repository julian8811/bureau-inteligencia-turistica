"""Series mensuales del anexo EMA, sin red ni el resto del extractor.

Ocupación nacional y de Antioquia desde 2019. Ingresos reales de
alojamiento (2019=100) desde 2015. El entrenamiento usa el valor del
anexo; el tablero lo muestra a 2 decimales.
"""
import re

MESES_LARGOS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
HOJA_OCUPACION = "4.2 Porc Mens Ocupación.reg"
HOJA_INGRESOS = "8.2 Ind empalmados.MMH"


def _filas_hoja(book, hoja, columnas):
    if hoja not in book.sheetnames:
        return []
    out = []
    anio = None
    for fila in book[hoja].iter_rows(values_only=True):
        if not fila:
            continue
        if fila[0] is not None:
            marca = re.match(r"\s*(\d{4})", str(fila[0]))
            if marca and int(marca.group(1)) > 1990:
                anio = int(marca.group(1))
        if not anio or not isinstance(fila[1], str) or fila[1].strip() not in MESES_LARGOS:
            continue
        if fila[columnas[0]] is None:
            continue
        mes = MESES_LARGOS.index(fila[1].strip()) + 1
        out.append((f"{anio:04d}-{mes:02d}", *[float(fila[c]) for c in columnas]))
    return out


def leer_anexo(path):
    import openpyxl

    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ocupacion = _filas_hoja(book, HOJA_OCUPACION, (2, 8))
        ingresos = [fila for fila in _filas_hoja(book, HOJA_INGRESOS, (3,)) if fila[0] >= "2015-01"]
    finally:
        book.close()
    if len(ocupacion) < 24 or len(ingresos) < 24:
        raise ValueError("anexo EMA sin las series mensuales esperadas")
    return {
        "ocupacion_nacional": ([f[0] for f in ocupacion], [f[1] for f in ocupacion]),
        "ocupacion_antioquia": ([f[0] for f in ocupacion], [f[2] for f in ocupacion]),
        "ingresos_reales": ([f[0] for f in ingresos], [f[1] for f in ingresos]),
    }
