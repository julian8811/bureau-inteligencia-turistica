#!/usr/bin/env python3
"""Genera proyecto PbixProj (TMDL) desde los CSV de powerbi-turismo/ y lo compila
a .PBIT con pbi-tools (CIU. Colegio Mayor de Antioquia).

Uso:
    python3 build_pbix.py [--compile|--nocompile]
    # requiere: pbi-tools.core en PATH (o $HOME/.pbi-tools) + dotnet 8 (DOTNET_ROOT)
Compilado:
    pbi-tools.core compile <carpeta> <salida.pbit> PBIT True
El .PBIT se abre en Power BI Desktop > Actualizar > Guardar como .PBIX.
"""
import csv
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent          # powerbi-turismo/
PROJ = BASE / "pbixproj-turismo"                # proyecto generado
OUT  = BASE / "turismo-2025-2026-Colmayor.pbit"

TABLE_DEFS = [
    # (csv, tabla, columnas[(nombre, tipo_tmdl, summarize, hidden, fmt)], pk?)
    ("09_dim_fuente.csv", None, None, None, None),  # placeholder
]
# Definición explícita por tabla: csv -> (tabla, [(col, tmdl_type, summarize, hidden)])
SCHEMA = {
 "01_fact_llegadas_global.csv": ("01_fact_llegadas_global", [
    ("periodo","string","none",False),("anio","int64","none",True),("trimestre","string","none",False),
    ("llegadas_M","double","sum",False),("var_pct","double","average",False),
    ("fuente","string","none",False),("fecha_pub","string","none",False),("id_fuente","string","none",True)]),
 "02_fact_llegadas_region_2025.csv": ("02_fact_llegadas_region_2025", [
    ("region","string","none",False),("llegadas_M_2025","double","sum",False),
    ("var_vs_2024_pct","double","average",False),("var_vs_2019_pct","double","average",False),
    ("fuente","string","none",False),("id_fuente","string","none",True)]),
 "03_fact_llegadas_region_H1_2026.csv": ("03_fact_llegadas_region_H1_2026", [
    ("region","string","none",False),("crec_H1_2026_pct","double","average",False),
    ("detalle","string","none",False),("fuente","string","none",False),("id_fuente","string","none",True)]),
 "04_fact_gasto.csv": ("04_fact_gasto", [
    ("indicador","string","none",False),("anio","int64","none",True),("valor_USD_T","double","sum",False),
    ("var_pct","double","average",False),("detalle","string","none",False),
    ("fuente","string","none",False),("id_fuente","string","none",True)]),
 "05_fact_eurostat_noches.csv": ("05_fact_eurostat_noches", [
    ("periodo","string","none",False),("noches_M","double","sum",False),("var_M","double","sum",False),
    ("var_pct","double","average",False),("origen","string","none",False),
    ("fuente","string","none",False),("id_fuente","string","none",True)]),
 "06_fact_aereo_iata.csv": ("06_fact_aereo_iata", [
    ("indicador","string","none",False),("periodo","int64","none",True),("valor","double","sum",False),
    ("unidad","string","none",False),("var_pct","double","average",False),
    ("fuente","string","none",False),("id_fuente","string","none",True)]),
 "07_fact_hotel_str.csv": ("07_fact_hotel_str", [
    ("mercado","string","none",False),("periodo","string","none",False),("ocup_pct","double","average",False),
    ("revpar_var","double","average",False),("nota","string","none",False),
    ("fuente","string","none",False),("id_fuente","string","none",True)]),
 "08_fact_colombia_Q1_2026.csv": ("08_fact_colombia_Q1_2026", [
    ("segmento","string","none",False),("categoria","string","none",False),("valor","double","sum",False),
    ("var_pct","double","average",False),("fuente","string","none",False),("id_fuente","string","none",True)]),
 "09_dim_fuente.csv": ("09_dim_fuente", [
    ("id_fuente","string","none",False),("base","string","none",False),("edicion","string","none",False),
    ("tipo","string","none",False),("acceso","string","none",False),("fecha_pub","string","none",False),("url_corta","string","none",False)]),
 "10_dim_region.csv": ("10_dim_region", [
    ("region","string","none",False),("orden","int64","none",False)]),
 "11_dim_periodo.csv": ("11_dim_periodo", [
    ("periodo","string","none",False),("anio","int64","none",True),("tipo_periodo","string","none",False)]),
 "12_dim_indicador_gasto.csv": ("12_dim_indicador_gasto", [
    ("indicador","string","none",False),("categoria","string","none",False)]),
 "13_dim_origen.csv": ("13_dim_origen", [
    ("origen","string","none",False)]),
 "14_dim_indicador_aereo.csv": ("14_dim_indicador_aereo", [
    ("indicador","string","none",False),("unidad","string","none",False),("categoria","string","none",False)]),
 "15_dim_mercado.csv": ("15_dim_mercado", [
    ("mercado","string","none",False),("tipo","string","none",False)]),
 "16_dim_segmento.csv": ("16_dim_segmento", [
    ("segmento","string","none",False)]),
}
MEASURES = {  # tabla -> [(nombre, dax, formatString)]
 "01_fact_llegadas_global": [
    ("Llegadas M", "SUM('01_fact_llegadas_global'[llegadas_M])", "#,##0.0"),
    ("Llegadas 2025", "CALCULATE(SUM('01_fact_llegadas_global'[llegadas_M]),'01_fact_llegadas_global'[periodo]=\"2025 anual\")", "#,##0"),
    ("Llegadas H1 2026", "CALCULATE(SUM('01_fact_llegadas_global'[llegadas_M]),'01_fact_llegadas_global'[periodo]=\"H1 2026\")", "#,##0"),
    ("Var Llegadas YoY %", "DIVIDE(CALCULATE(SUM('01_fact_llegadas_global'[llegadas_M]),'01_fact_llegadas_global'[periodo]=\"H1 2026\")-CALCULATE(SUM('01_fact_llegadas_global'[llegadas_M]),'01_fact_llegadas_global'[periodo]=\"H1 2025\"),CALCULATE(SUM('01_fact_llegadas_global'[llegadas_M]),'01_fact_llegadas_global'[periodo]=\"H1 2025\"))", "0.0%"),
 ],
 "02_fact_llegadas_region_2025": [
    ("Llegadas Region 2025 M", "SUM('02_fact_llegadas_region_2025'[llegadas_M_2025])", "#,##0"),
    ("Share Region 2025 %", "DIVIDE(SUM('02_fact_llegadas_region_2025'[llegadas_M_2025]),CALCULATE(SUM('02_fact_llegadas_region_2025'[llegadas_M_2025]),ALL('02_fact_llegadas_region_2025'[region])))", "0.0%"),
 ],
 "03_fact_llegadas_region_H1_2026": [
    ("Crec H1 2026 %", "AVERAGE('03_fact_llegadas_region_H1_2026'[crec_H1_2026_pct])/100", "0.0%"),
    ("Crec Min H1 %", "MIN('03_fact_llegadas_region_H1_2026'[crec_H1_2026_pct])/100", "0.0%"),
 ],
 "04_fact_gasto": [
    ("Receipts 2025 T", "CALCULATE(SUM('04_fact_gasto'[valor_USD_T]),'04_fact_gasto'[indicador]=\"Receipts\",'04_fact_gasto'[anio]=2025)", "$#,##0.00"),
    ("WTTC 2026F T", "CALCULATE(SUM('04_fact_gasto'[valor_USD_T]),'04_fact_gasto'[indicador]=\"WTTC PIB forecast\")", "$#,##0.00"),
    ("Export Total 2025 T", "CALCULATE(SUM('04_fact_gasto'[valor_USD_T]),'04_fact_gasto'[indicador]=\"Export total\",'04_fact_gasto'[anio]=2025)", "$#,##0.00"),
 ],
 "05_fact_eurostat_noches": [
    ("Noches M", "SUM('05_fact_eurostat_noches'[noches_M])", "#,##0"),
    ("Noches Intl Share %", "DIVIDE(CALCULATE(SUM('05_fact_eurostat_noches'[noches_M]),'05_fact_eurostat_noches'[origen]=\"Internacional\"),CALCULATE(SUM('05_fact_eurostat_noches'[noches_M]),ALL('05_fact_eurostat_noches'[origen])))", "0.0%"),
    ("Noches H1 2026 M", "CALCULATE(SUM('05_fact_eurostat_noches'[noches_M]),'05_fact_eurostat_noches'[periodo]=\"H1 2026\")", "#,##0"),
 ],
 "06_fact_aereo_iata": [
    ("Premium 2025 M", "CALCULATE(SUM('06_fact_aereo_iata'[valor]),'06_fact_aereo_iata'[indicador]=\"Premium intl\")", "#,##0.0"),
    ("RPK Q2 2026 %", "MAX('06_fact_aereo_iata'[var_pct])/100", "0.0%"),
    ("Pax 2026F M", "CALCULATE(SUM('06_fact_aereo_iata'[valor]),'06_fact_aereo_iata'[indicador]=\"Pax segmento\",'06_fact_aereo_iata'[periodo]=2026)", "#,##0"),
 ],
 "07_fact_hotel_str": [
    ("Ocup Global Mar-26 %", "CALCULATE(AVERAGE('07_fact_hotel_str'[ocup_pct]),'07_fact_hotel_str'[mercado]=\"Global\",'07_fact_hotel_str'[periodo]=\"mar-2026\")/100", "0.0%"),
    ("RevPAR Europa 2026F %", "CALCULATE(AVERAGE('07_fact_hotel_str'[revpar_var]),'07_fact_hotel_str'[mercado]=\"31 mercados Europa\",'07_fact_hotel_str'[periodo]=\"2026F\")/100", "0.0%"),
 ],
 "08_fact_colombia_Q1_2026": [
    ("Visitantes CO Q1 M", "CALCULATE(SUM('08_fact_colombia_Q1_2026'[valor]),'08_fact_colombia_Q1_2026'[categoria]=\"Extranjeros Q1 (M)\")", "#,##0.00"),
    ("Share Joven CO %", "CALCULATE(SUM('08_fact_colombia_Q1_2026'[valor]),'08_fact_colombia_Q1_2026'[categoria]=\"18-49 share\")/100", "0.0%"),
    ("Mujeres CO Share %", "CALCULATE(SUM('08_fact_colombia_Q1_2026'[valor]),'08_fact_colombia_Q1_2026'[categoria]=\"Mujeres share\")/100", "0.0%"),
    ("Bogota Share %", "CALCULATE(SUM('08_fact_colombia_Q1_2026'[valor]),'08_fact_colombia_Q1_2026'[categoria]=\"Bogota\")/100", "0.0%"),
    ("Divisas Q1 USD M", "CALCULATE(SUM('08_fact_colombia_Q1_2026'[valor]),'08_fact_colombia_Q1_2026'[categoria]=\"Q1 USD M\")", "#,##0"),
 ],
 "09_dim_fuente": [
    ("N Fuentes", "COUNTROWS('09_dim_fuente')", "#,##0"),
 ],
}
RELATIONSHIPS = [  # (fromTable.fromCol, toTable.toCol) — estrella: hechos -> dims, sin hecho-hecho
 ("01_fact_llegadas_global.anio", "dim_anio.anio"),
 ("01_fact_llegadas_global.periodo", "11_dim_periodo.periodo"),
 ("02_fact_llegadas_region_2025.region", "10_dim_region.region"),
 ("03_fact_llegadas_region_H1_2026.region", "10_dim_region.region"),
 ("04_fact_gasto.anio", "dim_anio.anio"),
 ("04_fact_gasto.indicador", "12_dim_indicador_gasto.indicador"),
 ("05_fact_eurostat_noches.origen", "13_dim_origen.origen"),
 ("06_fact_aereo_iata.periodo", "dim_anio.anio"),
 ("06_fact_aereo_iata.indicador", "14_dim_indicador_aereo.indicador"),
 ("07_fact_hotel_str.mercado", "15_dim_mercado.mercado"),
 ("08_fact_colombia_Q1_2026.segmento", "16_dim_segmento.segmento"),
 ("01_fact_llegadas_global.id_fuente", "09_dim_fuente.id_fuente"),
 ("02_fact_llegadas_region_2025.id_fuente", "09_dim_fuente.id_fuente"),
 ("03_fact_llegadas_region_H1_2026.id_fuente", "09_dim_fuente.id_fuente"),
 ("04_fact_gasto.id_fuente", "09_dim_fuente.id_fuente"),
 ("05_fact_eurostat_noches.id_fuente", "09_dim_fuente.id_fuente"),
 ("06_fact_aereo_iata.id_fuente", "09_dim_fuente.id_fuente"),
 ("07_fact_hotel_str.id_fuente", "09_dim_fuente.id_fuente"),
 ("08_fact_colombia_Q1_2026.id_fuente", "09_dim_fuente.id_fuente"),
]
DIM_ANIO_ROWS = [("2019","2019"),("2023","2023"),("2024","2024"),("2025","2025"),("2026","2026")]

def qn(name):  # quote TMDL identifier
    return name if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name or "") else f"'{name}'"

def m_escape(s):
    return (s or "").replace('"', '""')

def read_csv(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return reader.fieldnames, list(reader)
    except OSError as exc:
        raise SystemExit(f"No se pudo leer {path}: {exc}") from exc

def m_table(cols, rows):
    """cols: [(name, tmdl_type)] ; rows: [dict] -> M source text"""
    names = [c for c, _ in cols]
    hdr = "{" + ",".join(f'"{n}"' for n in names) + "}"
    lines = []
    for r in rows:
        vals = []
        for n, t in cols:
            v = (r.get(n) or "").strip()
            if v == "":
                vals.append("null")
                continue
            if t in ("int64", "double"):
                vals.append(v.replace(",", ""))
            else:
                vals.append(f'"{m_escape(v)}"')
        lines.append("      {" + ",".join(vals) + "}")
    body = ",\n".join(lines)
    type_map = {"string": "type text", "int64": "Int64.Type", "double": "type number"}
    type_pairs = ",".join(f'{{"{n}", {type_map[t]}}}' for n, t in cols)
    return (
 "let\n"
 f"        Source = #table(\n"
 f"            {hdr},\n"
 "            {\n"
 f"{body}\n"
 "            }\n"
 "        ),\n"
 f"        Typed = Table.TransformColumnTypes(Source, {{{type_pairs}}})\n"
 "    in\n"
 "        Typed"
    )

def table_tmdl(tname, cols, m_src):
    L = [f"table {qn(tname)}", ""]
    for c, t, summ, hid in cols:
        L.append(f"\tcolumn {qn(c)}")
        L.append(f"\t\tdataType: {t}")
        if hid:
            L.append("\t\tisHidden")
        if summ and summ != "none":
            L.append(f"\t\tsummarizeBy: {summ}")
        else:
            L.append("\t\tsummarizeBy: none")
        L.append(f"\t\tsourceColumn: {c}")
        L.append("")
    for mname, dax, fmt in MEASURES.get(tname, []):
        L.append(f"\tmeasure {qn(mname)} = {dax}")
        if fmt:
            L.append(f"\t\tformatString: {fmt}")
        L.append("")
    L.append(f"\tpartition {qn(tname)} = m")
    L.append("\t\tmode: import")
    L.append("\t\tsource =")
    for line in m_src.split("\n"):
        L.append("\t\t\t\t" + line if line.strip() else "")
    L.append("")
    L.append("\tannotation PBI_ResultType = Table")
    L.append("")
    return "\n".join(L)

def build():
    if PROJ.exists():
        import shutil
        try:
            shutil.rmtree(PROJ)
        except OSError as exc:
            raise SystemExit(f"No se pudo limpiar {PROJ}: {exc}") from exc
    (PROJ/"Model"/"tables").mkdir(parents=True)
    (PROJ/"Report"/"sections").mkdir(parents=True)
    (PROJ/"StaticResources"/"RegisteredResources").mkdir(parents=True)
    (PROJ/"StaticResources"/"SharedResources").mkdir(parents=True)
    # Tema Colmayor registrado en el propio informe (la cinta lee el tema
    # actual al abrir; sin tema declarado rompia con customTheme de undefined).
    (PROJ/"StaticResources"/"RegisteredResources"/"Colmayor.json").write_bytes((BASE/"Colmayor-theme.json").read_bytes())
    # Tema base oficial (el mismo que empaqueta Desktop en cada informe con
    # tema personalizado; la cinta resuelve config.themeCollection.baseTheme).
    (PROJ/"StaticResources"/"SharedResources"/"BaseThemes").mkdir(parents=True, exist_ok=True)
    (PROJ/"StaticResources"/"SharedResources"/"BaseThemes"/"CY19SU06.json").write_bytes((BASE/"BaseThemes-CY19SU06.json").read_bytes())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    (PROJ/".pbixproj.json").write_text(json.dumps({"version":"0.11","created":now,"lastModified":now}, indent=2), encoding="utf-8")
    (PROJ/"Version.txt").write_text("1.25", encoding="utf-8")
    (PROJ/"ReportMetadata.json").write_text(json.dumps({"Version":5,"AutoCreatedRelationships":[],"FileDescription":"","CreatedFrom":"Desktop","CreatedFromRelease":"2024.09"}, indent=2), encoding="utf-8")
    (PROJ/"ReportSettings.json").write_text(json.dumps({"Version":1,"ReportSettings":{},"QueriesSettings":{"TypeDetectionEnabled":True,"RelationshipImportEnabled":True,"RunBackgroundAnalysis":True,"Version":"2.81.5831.821"}}, indent=2), encoding="utf-8")

    tables = []
    # dim_anio sintética
    tables.append(("dim_anio", [("anio","int64","none",True),("etiqueta","string","none",False)],
                   [{"anio":a,"etiqueta":e} for a,e in DIM_ANIO_ROWS]))
    for csvf, (tname, cols) in SCHEMA.items():
        _, rows = read_csv(BASE/csvf)
        tables.append((tname, cols, rows))

    for tname, cols, rows in tables:
        mcols = [(c, t) for c, t, _, _ in cols]
        rdicts = [{k: (row.get(k) or "") for k, _ in mcols} for row in rows]
        msrc = m_table(mcols, rdicts)
        (PROJ/"Model"/"tables"/f"{tname}.tmdl").write_text("\ufeff" + table_tmdl(tname, cols, msrc), encoding="utf-8")

    (PROJ/"Model"/"database.tmdl").write_text("\ufeffdatabase 'Turismo 2025-2026 Colmayor'\n\tcompatibilityLevel: 1550\n", encoding="utf-8")
    ml = ["\ufeffmodel Model", "\tculture: es-ES", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
          "\tsourceQueryCulture: es-ES", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", ""]
    for tname, _, _ in tables:
        ml.append(f"ref table {qn(tname)}")
    (PROJ/"Model"/"model.tmdl").write_text("\n".join(ml) + "\n", encoding="utf-8")
    rl = []
    for fc, tc in RELATIONSHIPS:
        ft, fcol = fc.split(".")
        tt, tcol = tc.split(".")
        rl.append(f"relationship {uuid.uuid4()}\n\tfromColumn: {qn(ft)}.{qn(fcol)}\n\ttoColumn: {qn(tt)}.{qn(tcol)}\n")
    (PROJ/"Model"/"relationships.tmdl").write_text("\ufeff" + "\n".join(rl), encoding="utf-8")

    # Diagrama: formato v1.0.0 de referencia (DiagramEdgeService resuelve los
    # nodos por nombre; el esquema ordinal/location/zIndex dejaba los extremos
    # de las aristas en null y el Model view rompia con TypeError).
    names = [tname for tname, _, _ in tables]
    nodes, max_x, max_y = [], 0.0, 0.0
    for i, (tname, cols, _) in enumerate(tables):
        w = 234.0
        h = float(70 + 20 * (len(cols) + len(MEASURES.get(tname, []))))
        x = float(20 + (i % 5) * 260)
        y = float(20 + (i // 5) * 340)
        nodes.append({"height": h, "layedOut": True, "left": x,
                      "nodeIndex": tname, "top": y, "width": w})
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)
    (PROJ/"DiagramLayout.json").write_text(json.dumps({
        "version": "1.0.0",
        "diagrams": [{
            "name": "All tables",
            "zoomValue": 60,
            "isDefault": True,
            "tables": names,
            "layout": {
                "boundingBoxWidth": max_x + 20.0,
                "boundingBoxHeight": max_y + 20.0,
                "boundingBoxPosition": {"x": 0, "y": 0},
                "nodes": nodes}}]}, indent=2), encoding="utf-8")

    # Report: 6 paginas con visuales reales ligados al modelo
    (PROJ/"Report"/"report.json").write_text(json.dumps({"id":0,"layoutOptimization":0,"resourcePackages":[],"theme":"Colmayor.json"}, indent=2), encoding="utf-8")
    (PROJ/"Report"/"config.json").write_text(json.dumps({
        "version":"5.9","activeSectionIndex":0,"defaultDrillFilterOtherVisuals":True,
        "themeCollection":{"baseTheme":{"name":"CY19SU06","version":"5.3","type":2},
                            "customTheme":{"name":"Colmayor.json","version":"5.4","type":1}},
        "slowDataSourceSettings":{"isCrossHighlightingDisabled":False,"isSlicerSelectionsButtonEnabled":False,"isFilterSelectionsButtonEnabled":False,"isFieldWellButtonEnabled":False,"isApplyAllButtonEnabled":False},
        "linguisticSchemaSyncVersion":2,
        "settings":{"useNewFilterPaneExperience":True,"allowChangeFilterTypes":True,"useStylableVisualContainerHeader":True,"exportDataMode":1,"allowDataPointLassoSelect":True}}, indent=2), encoding="utf-8")

    def _proto_measure(table, measure):
        return {"Version":2,"From":[{"Name":"a","Entity":table}],
            "Select":[{"Measure":{"Expression":{"SourceRef":{"Source":"a"}},"Property":measure},"Name":f"{table}.{measure}"}],
            "OrderBy":[{"Direction":2,"Expression":{"Measure":{"Expression":{"SourceRef":{"Source":"a"}},"Property":measure}}}]}

    def _proto_cat_val(table, cat, val, func):
        yref = f"{'Sum' if func==0 else 'Average'}({table}.{val})"
        return {"Version":2,"From":[{"Name":"t","Entity":table}],
            "Select":[{"Column":{"Expression":{"SourceRef":{"Source":"t"}},"Property":cat},"Name":f"{table}.{cat}"},
                {"Aggregation":{"Expression":{"Column":{"Expression":{"SourceRef":{"Source":"t"}},"Property":val}},"Function":func},"Name":yref}],
            "OrderBy":[{"Direction":2,"Expression":{"Aggregation":{"Expression":{"Column":{"Expression":{"SourceRef":{"Source":"t"}},"Property":val}},"Function":func}}}]} , yref

    def _proto_cols(table, cols):
        return {"Version":2,"From":[{"Name":"t","Entity":table}],
            "Select":[{"Column":{"Expression":{"SourceRef":{"Source":"t"}},"Property":c},"Name":f"{table}.{c}"} for c in cols]}

    def _cfg_textbox(txt, size, bold):
        run = {"value": txt, "textStyle": {"fontSize": f"{size}pt"}}
        if bold:
            run["textStyle"].update({"fontWeight": "bold", "color": "#172139"})
        return {"visualType":"textbox","drillFilterOtherVisuals":True,
            "objects":{"general":[{"properties":{"paragraphs":[{"textRuns":[run]}]}}]}}

    def _cfg_card(table, measure):
        qref = f"{table}.{measure}"
        return {"visualType":"card","projections":{"Values":[{"queryRef":qref}]},
            "prototypeQuery":_proto_measure(table, measure),"drillFilterOtherVisuals":True}

    def _cfg_column(table, cat, val, func):
        proto, yref = _proto_cat_val(table, cat, val, func)
        return {"visualType":"clusteredColumnChart",
            "projections":{"Category":[{"queryRef":f"{table}.{cat}","active":True}],"Y":[{"queryRef":yref}]},
            "prototypeQuery":proto,"drillFilterOtherVisuals":True}

    def _cfg_table(table, cols):
        return {"visualType":"tableEx",
            "projections":{"Values":[{"queryRef":f"{table}.{c}"} for c in cols]},
            "prototypeQuery":_proto_cols(table, cols),"drillFilterOtherVisuals":True}

    def _cfg_slicer(table, col):
        return {"visualType":"slicer",
            "projections":{"Values":[{"queryRef":f"{table}.{col}"}]},
            "prototypeQuery":_proto_cols(table, [col]),"drillFilterOtherVisuals":True}

    # (titulo pagina, [(tipo, args, x, y, w, h)]) — tipos: text | card | column | table | slicer
    pages = [
        ("01 Portada", [
            ("text", ("INFORME TURISMO 2025 \u2013 2026 \u00b7 I.U. Colegio Mayor de Antioquia", 26, True), 60, 30, 1160, 70),
            ("text", ("Datos globales, regionales y tendencias del sector \u2014 UN Tourism \u00b7 WTTC \u00b7 IATA \u00b7 Eurostat \u00b7 STR \u00b7 Phocuswright \u00b7 Amadeus", 12, False), 60, 105, 1160, 40),
            ("card", ("01_fact_llegadas_global", "Llegadas 2025"), 60, 170, 270, 150),
            ("card", ("01_fact_llegadas_global", "Llegadas H1 2026"), 360, 170, 270, 150),
            ("card", ("04_fact_gasto", "Receipts 2025 T"), 660, 170, 270, 150),
            ("card", ("04_fact_gasto", "WTTC 2026F T"), 960, 170, 260, 150),
            ("text", (f"C\u00f3mo usar: abrir el .PBIT en Power BI Desktop > Actualizar > Guardar como .PBIX (tema Colmayor incluido). Fuentes y corte en la p\u00e1gina 06. Compilaci\u00f3n {stamp}.", 11, False), 60, 350, 1160, 60),
            ("table", ("09_dim_fuente", ["base", "edicion", "acceso", "fecha_pub"]), 60, 430, 1160, 250),
        ]),
        ("02 Llegadas globales", [
            ("text", ("Llegadas internacionales 2023\u20132026 \u00b7 UN Tourism", 20, True), 60, 20, 1160, 60),
            ("column", ("01_fact_llegadas_global", "periodo", "llegadas_M", 0), 60, 100, 760, 380),
            ("card", ("01_fact_llegadas_global", "Llegadas H1 2026"), 850, 100, 370, 150),
            ("slicer", ("01_fact_llegadas_global", "periodo"), 850, 270, 370, 210),
            ("text", ("Nota: anual, H1 y trimestres se solapan (H1 = Q1+Q2). Comparar barras, no sumarlas. H1 2026: 690 M (+0,4%).", 11, False), 60, 500, 1160, 60),
            ("text", ("2023: 1.260 M \u00b7 2024: 1.400 M (+11%) \u00b7 2025: 1.520 M (+4%, r\u00e9cord) \u00b7 Q1 2026: 307 M (+2%).", 11, False), 60, 570, 1160, 60),
        ]),
        ("03 Regiones", [
            ("text", ("Regiones 2025 y H1 2026 \u00b7 UN Tourism", 20, True), 60, 20, 1160, 60),
            ("column", ("02_fact_llegadas_region_2025", "region", "llegadas_M_2025", 0), 60, 100, 570, 380),
            ("column", ("03_fact_llegadas_region_H1_2026", "region", "crec_H1_2026_pct", 1), 660, 100, 560, 380),
            ("text", ("2025: Europa 793 M (52%) \u00b7 Asia-Pac 331 \u00b7 Am\u00e9ricas 218 \u00b7 Med.O ~100 \u00b7 \u00c1frica 81. H1 2026: \u00c1frica +4%, Europa +3%, Am\u00e9ricas +2%, Asia +1%, Med.O \u221222%.", 11, False), 60, 500, 1160, 60),
            ("text", ("Sin mapa coropl\u00e9tico: las regiones agregadas (Europa, Asia-Pac\u00edfico...) no son pa\u00edses y el mapa no las geocodifica. Las barras son la comparativa correcta.", 11, False), 60, 570, 1160, 60),
        ]),
        ("04 Gasto", [
            ("text", ("Gasto tur\u00edstico y peso econ\u00f3mico \u00b7 UN Tourism \u00b7 WTTC \u00b7 Phocuswright", 20, True), 60, 20, 1160, 60),
            ("card", ("04_fact_gasto", "Receipts 2025 T"), 60, 100, 350, 150),
            ("card", ("04_fact_gasto", "WTTC 2026F T"), 440, 100, 350, 150),
            ("text", ("Receipts +5% vs llegadas +4%: el precio tira m\u00e1s que el volumen en 2025.", 11, False), 820, 100, 400, 150),
            ("table", ("04_fact_gasto", ["indicador", "anio", "valor_USD_T", "var_pct"]), 60, 270, 1160, 330),
        ]),
        ("05 Europa Aereo Hotel", [
            ("text", ("Europa + a\u00e9reo + hoteler\u00eda \u00b7 Eurostat \u00b7 IATA \u00b7 STR", 20, True), 60, 20, 1160, 60),
            ("column", ("05_fact_eurostat_noches", "periodo", "noches_M", 0), 60, 100, 1160, 300),
            ("table", ("06_fact_aereo_iata", ["indicador", "periodo", "valor", "unidad"]), 60, 420, 570, 240),
            ("table", ("07_fact_hotel_str", ["mercado", "periodo", "ocup_pct", "revpar_var"]), 650, 420, 570, 240),
        ]),
        ("06 Colombia y Fuentes", [
            ("text", ("Colombia Q1 2026 + trazabilidad de fuentes", 20, True), 60, 20, 1160, 60),
            ("card", ("08_fact_colombia_Q1_2026", "Visitantes CO Q1 M"), 60, 100, 350, 150),
            ("card", ("08_fact_colombia_Q1_2026", "Share Joven CO %"), 440, 100, 350, 150),
            ("text", ("1,36 M extranjeros (+4,4%) \u00b7 Bogot\u00e1 35% \u00b7 Divisas USD 3.146 M (+9,4%). Detalle por segmento en la tabla.", 11, False), 820, 100, 400, 150),
            ("table", ("08_fact_colombia_Q1_2026", ["segmento", "categoria", "valor", "var_pct"]), 60, 270, 1160, 200),
            ("table", ("09_dim_fuente", ["base", "edicion", "acceso", "fecha_pub"]), 60, 490, 1160, 190),
        ]),
    ]
    for idx, (title, visuals) in enumerate(pages):
        sec = PROJ/"Report"/"sections"/f"{idx+1:02d}_{title.split(' ',1)[1]}"
        (sec/"visualContainers").mkdir(parents=True)
        (sec/"section.json").write_text(json.dumps({"displayName":title,"displayOption":1,"height":720,"name":f"ReportSection{idx}","ordinal":idx,"width":1280}, indent=2), encoding="utf-8")
        (sec/"config.json").write_text("{}", encoding="utf-8")
        (sec/"filters.json").write_text("[]", encoding="utf-8")
        for j, (vtype, args, x, y, w, h) in enumerate(visuals):
            vid = uuid.uuid4().hex[:8]
            vdir = sec/"visualContainers"/f"{j:05d}_{vtype} ({vid[:5]})"
            vdir.mkdir()
            (vdir/"visualContainer.json").write_text(json.dumps({"height":float(h),"width":float(w),"x":float(x),"y":float(y),"z":1000+j}, indent=2), encoding="utf-8")
            if vtype == "text":
                single = _cfg_textbox(*args)
            elif vtype == "card":
                single = _cfg_card(*args)
            elif vtype == "column":
                single = _cfg_column(*args)
            elif vtype == "table":
                single = _cfg_table(*args)
            elif vtype == "slicer":
                single = _cfg_slicer(*args)
            else:
                raise ValueError(f"tipo visual desconocido: {vtype}")
            (vdir/"config.json").write_text(json.dumps({
                "name": uuid.uuid4().hex[:21],
                "layouts": [{"id":0,"position":{"x":float(x),"y":float(y),"z":1000+j,"width":float(w),"height":float(h)}}],
                "singleVisual": single}, indent=2), encoding="utf-8")
    print(f"Proyecto generado en {PROJ} ({len(tables)} tablas, {len(pages)} paginas con visuales)")

def compile_pbit():
    env = dict(os.environ)
    env["DOTNET_ROOT"] = os.path.expanduser("~/.dotnet")
    env["PATH"] = os.path.expanduser("~/.pbi-tools") + ":" + env.get("PATH","")
    exe = os.path.expanduser("~/.pbi-tools/pbi-tools.core")
    if OUT.exists():
        OUT.unlink()
    cmd = [exe, "compile", "-folder", str(PROJ), "-outPath", str(OUT), "-format", "PBIT", "-overwrite"]
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    print(r.stdout[-3000:])
    print(r.stderr[-2000:], file=sys.stderr)
    if OUT.exists():
        print(f"OK: {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
        fixup_pbit()
        return True
    print("FALLO la compilación (ver arriba)")
    return False

def fixup_pbit():
    """Enlaza el tema en el Layout compilado (pbi-tools empaqueta el tema
    como pieza suelta pero no genera la entrada resourcePackages que el
    Desktop usa para resolver el tema actual; esquema copiado de un PBIX
    real con tema personalizado: paquete RegisteredResources/type 1,
    item del tema type 201 con path = nombre del archivo)."""
    import zipfile as _zip
    lay_name = "Report/Layout"
    try:
        with _zip.ZipFile(OUT, "r") as zin:
            raw = zin.read(lay_name).decode("utf-16-le")
            others = [(i.filename, zin.read(i.filename)) for i in zin.infolist() if i.filename != lay_name]
        lay = json.loads(raw)
    except (KeyError, ValueError, UnicodeError) as exc:
        raise SystemExit(f"fixup: no se pudo leer {lay_name} del PBIT recien compilado: {exc}") from exc
    lay["resourcePackages"] = [{"resourcePackage": {
        "name": "SharedResources", "type": 2,
        "items": [{"type": 202, "path": "BaseThemes/CY19SU06.json", "name": "CY19SU06"}],
        "disabled": False}}, {"resourcePackage": {
        "name": "RegisteredResources", "type": 1,
        "items": [{"type": 201, "path": "Colmayor.json", "name": "Colmayor.json"}],
        "disabled": False}}]
    blob = json.dumps(lay, ensure_ascii=False).encode("utf-16-le")
    tmp = OUT.with_suffix(".tmp.pbit")
    with _zip.ZipFile(tmp, "w", _zip.ZIP_DEFLATED) as zout:
        for fname, data in others:
            zout.writestr(fname, data)
        zout.writestr(lay_name, blob)
    tmp.replace(OUT)
    print(f"fixup: tema enlazado en {lay_name}")

if __name__ == "__main__":
    build()
    if "--nocompile" not in sys.argv:
        compile_pbit()
