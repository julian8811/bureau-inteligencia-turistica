#!/usr/bin/env python3
"""Consumo turistico -> export/tableros_bureau/consumo_2025_2026.json.

Agrega 3 capas de gasto ya verificadas (sin inventar, sin APIs bancarias cerradas):

1. Ticket promedio por pais emisor (SIT Medellin, reusado de sit_emisores_2025_2026.json).
2. Gasto extranjero en Colombia = turismo receptor DANE CST 2023-2025pr
   (bol-CST-2025.pdf, valores a precios corrientes, base 2015).
3. Gasto turistico Medellin con tarjeta (SITE + Credibanco + CityData,
   Alcaldia 2026-07-22: $4 billones medibles / 16M tx / ~$9 billones estimado).

Solo stdlib + json. Defensivo: SIT ausente -> seccion en null + nota,
exit 0, nunca tumba el build. Valores ausentes -> null, jamas 0.
"""

import datetime
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
SIT_IN = BASE / "tableros_bureau" / "sit_emisores_2025_2026.json"
OUT = BASE / "tableros_bureau" / "consumo_2025_2026.json"

ID = "bureau-consumo"
VENTANA = "2023-2025"
FUENTE = "DANE CST + SIT Medellin + SITE/Credibanco/CityData (agregados publicos)"

# Gasto extranjero en Colombia (turismo receptor), miles de millones COP corrientes.
# Fuente: DANE bol-CST-2025.pdf Tabla 1 (2024p provisional, 2025pr preliminar).
# Verificado 2026-05-21. No incluye extrapolacion propia.
GASTO_RECEPTOR = {
    "unidad": "miles_de_millones_cop_corrientes",
    "estado": {"2023": "definitivo", "2024": "provisional", "2025": "preliminar"},
    "total": {"2023": 47937, "2024": 50483, "2025": 54704},
    "flujos_personas": {"2023": 3883877, "2024": 4421053, "2025": 4589891},
    "pernoctaciones": {"2023": 64432305, "2024": 73343862, "2025": 76144862},
    "desglose_2025": {
        "transporte_aereo_pasajeros": 13991,
        "alimentos_bebidas": 13296,
        "alojamiento_visitantes": 7552,
        "transporte_carretera": 6256,
        "culturales_deportivos_recreativos": 5302,
        "bienes_consumo": 6380,
        "agencias_viajes_reservas": 302,
        "otros_servicios": 1625,
    },
    "fuente_url": "https://www.dane.gov.co/files/operaciones/CST/bol-CST-2025.pdf",
}

# Gasto turistico Medellin 2025 con tarjeta.
# Fuente: Alcaldia de Medellin 2026-07-22, analisis SITE + Credibanco + CityData.
GASTO_MEDELLIN = {
    "unidad": "millones_cop",
    "gasto_tarjeta_medible": 4000000000000,
    "transacciones_tarjeta": 16000000,
    "cobertura_credibanco_pct": 45,
    "gasto_total_estimado": 9000000000000,
    "nota_estimado": "Extrapolacion SITE: Credibanco procesa ~45% de tx con tarjeta; sin contar efectivo.",
    "split_medible": {"internacional_pct": 49.1, "nacional_pct": 50.9},
    "top_internacional": [
        {"pais": "Estados Unidos", "gasto": 906000000000},
        {"pais": "Mercado #2", "gasto": 96000000000},
    ],
    "top_nacional": [
        {"ciudad": "Bogota", "gasto": 619000000000},
        {"ciudad": "Cali", "gasto": 65000000000},
        {"ciudad": "Barranquilla", "gasto": 42000000000},
        {"ciudad": "Cartagena", "gasto": 39000000000},
        {"ciudad": "Pereira", "gasto": 30000000000},
    ],
    "fuente_url": "https://www.medellin.gov.co/es/sala-de-prensa/noticias/medellin-movio-alrededor-de-9-billones-en-turismo-durante-2025-segun-analisis-de-datos-del-sector/",
}


def hoy():
    return datetime.date.today().isoformat()


def main():
    notas = []
    mercados = []
    try:
        sit = json.loads(SIT_IN.read_text(encoding="utf-8"))
        for m in sit.get("mercados", []):
            lleg = m.get("llegadas")
            ticket = m.get("ticket_prom_cop")
            if isinstance(lleg, (int, float)) and isinstance(ticket, (int, float)):
                estimado = int(lleg * ticket)
            else:
                estimado = None
            mercados.append(
                {
                    "pais": m.get("mercado"),
                    "anio": int(m.get("periodo") or 2025),
                    "llegadas": lleg,
                    "ticket_prom_cop": ticket,
                    "estancia_media_dias": m.get("estancia_media_dias"),
                    "gasto_estimado_cop": estimado,
                    "nota": "gasto_estimado = llegadas * ticket_prom cuando ambos existen; sino null",
                }
            )
    except Exception as exc:
        notas.append(f"SIT no disponible ({type(exc).__name__}): serie por-pais en null.")
        mercados = []

    payload = {
        "id": ID,
        "generado": hoy(),
        "ventana": VENTANA,
        "fuente": FUENTE,
        "licencia": "Agregados propios del ETL; fuentes primarias DANE / SIT / Alcaldia-SITE. Sin datos bancarios individuales (reserva art. 15 Const. + Ley 1266/1581).",
        "universo": "Gasto extranjero en Colombia (receptor CST), ticket por mercado emisor SIT, gasto Medellin con tarjeta SITE.",
        # 1. ticket por pais, listo para ?serie=ticket_prom / gasto_estimado
        "serie_mercados": mercados,
        # 2. gasto extranjero en Colombia, listo para ?serie=gasto_receptor
        "gasto_extranjero_co": GASTO_RECEPTOR,
        # 3. gasto Medellin tarjeta
        "gasto_medellin": GASTO_MEDELLIN,
        "series_disponibles": [
            "llegadas (de pais_dashboard, ya existente)",
            "ticket_prom_cop (serie_mercados)",
            "gasto_estimado_cop (serie_mercados, llegadas*ticket)",
            "gasto_receptor_total (gasto_extranjero_co.total)",
            "gasto_medellin_tarjeta (gasto_medellin)",
        ],
        "notas": notas
        + [
            "CST 2024 provisional / 2025 preliminar: pueden revisarse en proxima publicacion DANE.",
            "Ticket SIT solo donde el informe trae ticket POS; Francia queda null (sin vuelo directo ni ticket publicado).",
            "Gasto Medellin internacional/nacional es sobre lo medible con tarjeta; el 25.5% nacional-real descuenta movilidad Valle de Aburra/Rionegro (informe SITE).",
        ],
        "estado": "ok",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"consumo ok -> {OUT} ({len(mercados)} mercados)")


if __name__ == "__main__":
    main()
