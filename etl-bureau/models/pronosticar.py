"""Pronóstico a 6 meses para el tablero.

Tres modelos, un ensayo y una regla de desempate. El ensayo son los
últimos 6 meses observados. Gana el menor error absoluto (MAE). Si otro
queda a menos del 2 %, se publica el más simple: estacional, luego
Holt-Winters, luego el gradiente. La banda es el percentil 80 de ese
error; no es un intervalo de confianza.

Con 54 a 96 meses no se entrena una red. Operaciones, BTS, IPC, OWID,
SISAIRE, TRM y EVI quedan fuera: el grano o el largo no alcanzan.
"""
import json
import math
import os
import warnings
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "export" / "tableros_bureau" / "pronosticos.json"
SEGURIDAD = BASE / "export" / "tableros_bureau" / "seguridad_2025_2026.json"
INSUMOS = Path(__file__).resolve().parent / "insumos" / "series_mensuales.json"

HOLDOUT = 6
HORIZONTE = 6
PERIODO = 12
MARGEN = 1.02
ETIQUETAS = {
    "estacional": "repetir el mismo mes del año anterior",
    "holt_winters": "Holt-Winters",
    "gradiente": "gradiente con rezagos",
}
ORDEN = ("estacional", "holt_winters", "gradiente")

NOTA_BANDA = (
    "La banda es el percentil 80 del error absoluto en los últimos 6 meses "
    "observados. No es un intervalo de confianza."
)
NOTA_CAUSA = "No mide causas, reservas ni el CRM. Solo prolonga la serie mensual observada."


def percentil(valores, p):
    xs = sorted(float(v) for v in valores)
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (p / 100.0)
    lo = int(math.floor(k))
    hi = int(math.ceil(k))
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def reparar(valores):
    """Un punto por debajo del 15 % de la mediana y del 20 % de ambos vecinos
    se reemplaza por el promedio de esos vecinos. El índice queda en `tocados`.
    """
    out = [float(v) for v in valores]
    if len(out) < 3:
        return out, []
    med = percentil(out, 50)
    if med <= 0:
        return out, []
    tocados = []
    for i in range(1, len(out) - 1):
        v, a, b = out[i], out[i - 1], out[i + 1]
        if v < 0.15 * med and v < 0.2 * a and v < 0.2 * b:
            out[i] = (a + b) / 2.0
            tocados.append(i)
    return out, tocados


def caer_ceros_iniciales(periodos, valores):
    i = 0
    while i < len(valores) and float(valores[i]) == 0.0:
        i += 1
    return list(periodos[i:]), [float(v) for v in valores[i:]], list(periodos[:i])


def elegir(maes):
    """Menor MAE. Dentro del 2 % gana el más simple."""
    presentes = {k: float(v) for k, v in maes.items() if v is not None}
    if not presentes:
        raise ValueError("sin modelos")
    mejor = min(presentes.values())
    umbral = 0.0 if mejor == 0 else mejor * MARGEN
    for nombre in ORDEN:
        if nombre in presentes and presentes[nombre] <= umbral + 1e-9:
            return nombre
    return min(presentes, key=presentes.get)


def pronostico_estacional(train, horizonte, periodo=PERIODO):
    if len(train) < periodo:
        return None
    out = []
    for h in range(1, horizonte + 1):
        out.append(float(train[-periodo + (h - 1) % periodo]))
    return out


def pronostico_holt(train, horizonte):
    if len(train) < PERIODO * 2:
        return None
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
    except Exception:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            modelo = ExponentialSmoothing(
                [float(v) for v in train],
                trend="add",
                seasonal="add",
                seasonal_periods=PERIODO,
                initialization_method="estimated",
            )
            ajuste = modelo.fit(optimized=True, method="L-BFGS-B")
            pred = [float(v) for v in ajuste.forecast(horizonte)]
    except Exception:
        return None
    if not pred or any(not math.isfinite(v) for v in pred):
        return None
    return pred


def _mes_siguiente(mes, pasos):
    return ((int(mes) - 1 + pasos) % 12) + 1


def pronostico_gradiente(train, meses, horizonte):
    if len(train) < PERIODO * 2 or len(meses) != len(train):
        return None
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except Exception:
        return None
    x, y = [], []
    for i in range(PERIODO, len(train)):
        x.append([float(train[i - 1]), float(train[i - 12]), float(meses[i])])
        y.append(float(train[i]))
    if len(x) < 12:
        return None
    try:
        reg = HistGradientBoostingRegressor(
            max_depth=3,
            max_iter=100,
            learning_rate=0.08,
            min_samples_leaf=4,
            random_state=0,
        )
        reg.fit(x, y)
        hist = [float(v) for v in train]
        ultimo = int(meses[-1])
        pred = []
        for h in range(horizonte):
            mes = _mes_siguiente(ultimo, h + 1)
            punto = float(reg.predict([[hist[-1], hist[-12], float(mes)]])[0])
            if not math.isfinite(punto):
                return None
            pred.append(punto)
            hist.append(punto)
        return pred
    except Exception:
        return None


def mae(real, pred):
    return sum(abs(float(a) - float(b)) for a, b in zip(real, pred)) / len(real)


def mape(real, pred):
    pares = [(float(a), float(b)) for a, b in zip(real, pred) if float(a) != 0.0]
    if not pares:
        return None
    return 100.0 * sum(abs(a - b) / abs(a) for a, b in pares) / len(pares)


def recortar(valor, piso, techo):
    v = float(valor)
    if piso is not None:
        v = max(float(piso), v)
    if techo is not None:
        v = min(float(techo), v)
    return v


def redondear(valor, decimales):
    v = round(float(valor), int(decimales))
    if int(decimales) == 0:
        return int(v)
    return v


def siguiente_periodo(periodo, pasos=1):
    anio = int(periodo[:4])
    mes = int(periodo[5:7])
    mes += int(pasos)
    anio += (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    return f"{anio:04d}-{mes:02d}"


def _librerias():
    tiene = {"holt_winters": True, "gradiente": True}
    try:
        import statsmodels.tsa.holtwinters  # noqa: F401
    except Exception:
        tiene["holt_winters"] = False
    try:
        import sklearn.ensemble  # noqa: F401
    except Exception:
        tiene["gradiente"] = False
    return tiene


def evaluar(valores, meses, horizonte):
    train = valores[:-horizonte]
    reales = valores[-horizonte:]
    meses_train = meses[:-horizonte]
    brutos = {
        "estacional": pronostico_estacional(train, horizonte),
        "holt_winters": pronostico_holt(train, horizonte),
        "gradiente": pronostico_gradiente(train, meses_train, horizonte),
    }
    return train, reales, brutos


def _nota_eleccion(ganador, maes):
    puro = min(maes, key=maes.get)
    if ganador == puro:
        return (
            f"Se publica «{ETIQUETAS[ganador]}»: tuvo el menor error absoluto "
            f"en los últimos {HOLDOUT} meses."
        )
    return (
        f"Se publica «{ETIQUETAS[ganador]}»: su error queda a menos del 2 % de "
        f"«{ETIQUETAS[puro]}» y, en ese margen, se queda el modelo más simple."
    )


def proyectar(modelo, valores, meses):
    if modelo == "estacional":
        return pronostico_estacional(valores, HORIZONTE)
    if modelo == "holt_winters":
        return pronostico_holt(valores, HORIZONTE)
    if modelo == "gradiente":
        return pronostico_gradiente(valores, meses, HORIZONTE)
    return None


def construir_serie(spec, periodos, valores, libs):
    periodos = list(periodos)
    valores = [float(v) for v in valores]
    notas = list(spec.get("notas") or [])
    if spec.get("caer_ceros"):
        periodos, valores, caidos = caer_ceros_iniciales(periodos, valores)
        if caidos:
            notas.append(
                "Los meses "
                + ", ".join(caidos)
                + " abren la serie en 0 y el resto no. Se dejan fuera del modelo."
            )
    if len(periodos) < PERIODO + HOLDOUT:
        return None
    valores, tocados = reparar(valores)
    reparados = [periodos[i] for i in tocados]
    if reparados:
        notas.append(
            "Se corrigió "
            + ", ".join(reparados)
            + ": el valor era menor al 15 % de la mediana y al 20 % de los dos meses vecinos. "
            "Entra el promedio de esos vecinos, no el punto crudo."
        )
    meses = [int(p[5:7]) for p in periodos]
    _, reales, brutos = evaluar(valores, meses, HOLDOUT)
    comparacion = []
    maes = {}
    for nombre in ORDEN:
        pred = brutos.get(nombre)
        if pred is None:
            if nombre != "estacional" and not libs.get(nombre, True):
                notas.append(f"No se entrenó {ETIQUETAS[nombre]}: falta la librería.")
            elif nombre != "estacional":
                notas.append(f"No se ajustó {ETIQUETAS[nombre]} en esta serie.")
            continue
        pred_r = [redondear(recortar(v, spec.get("piso"), spec.get("techo")), spec["decimales"]) for v in pred]
        error = mae(reales, pred_r)
        maes[nombre] = error
        comparacion.append({
            "modelo": nombre,
            "etiqueta": ETIQUETAS[nombre],
            "mae": redondear(error, 2 if spec["decimales"] else 1),
            "mape": None if mape(reales, pred_r) is None else redondear(mape(reales, pred_r), 1),
        })
    if "estacional" not in maes:
        return None
    ganador = elegir(maes)
    futuro = proyectar(ganador, valores, meses)
    if not futuro:
        ganador = "estacional"
        futuro = pronostico_estacional(valores, HORIZONTE)
    mas_fino = min(maes, key=maes.get)
    dec = spec["decimales"]
    piso, techo = spec.get("piso"), spec.get("techo")
    pred_hold = [
        redondear(recortar(v, piso, techo), dec)
        for v in brutos[ganador]
    ]
    errores = [abs(float(a) - float(b)) for a, b in zip(reales, pred_hold)]
    banda = redondear(percentil(errores, 80), dec)
    corte = periodos[-1]
    puntos = []
    for h, bruto in enumerate(futuro, start=1):
        valor = redondear(recortar(bruto, piso, techo), dec)
        bajo = redondear(recortar(float(valor) - float(banda), piso, techo), dec)
        alto = redondear(recortar(float(valor) + float(banda), piso, techo), dec)
        puntos.append({
            "periodo": siguiente_periodo(corte, h),
            "valor": valor,
            "bajo": bajo,
            "alto": alto,
        })
    hist = []
    for periodo, valor in list(zip(periodos, valores))[-24:]:
        hist.append({"periodo": periodo, "valor": redondear(valor, dec)})
    fila_mae = next(c for c in comparacion if c["modelo"] == ganador)
    ultimo_obs = float(valores[-1])
    if ultimo_obs and float(banda) >= 0.3 * abs(ultimo_obs):
        notas.append(
            f"La banda (±{banda} {spec['unidad']}) es amplia frente al último mes "
            f"({redondear(ultimo_obs, dec)} {spec['unidad']}): el ensayo se mueve mucho "
            "y el punto no debe leerse como una meta."
        )
    if ganador == "gradiente":
        cola = [redondear(recortar(v, piso, techo), dec) for v in futuro[-3:]]
        if len(cola) == 3 and len(set(cola)) == 1:
            notas.append(
                "Los últimos meses del gradiente salen iguales: al usar su propio "
                "pronóstico como entrada, el árbol deja de mover la serie."
            )
    notas.append(_nota_eleccion(ganador, maes))
    notas.append(NOTA_BANDA)
    notas.append(NOTA_CAUSA)
    return {
        "id": spec["id"],
        "tab": spec["tab"],
        "nombre": spec["nombre"],
        "unidad": spec["unidad"],
        "decimales": dec,
        "modelo": ganador,
        "modelo_etiqueta": ETIQUETAS[ganador],
        "corte": corte,
        "holdout_meses": HOLDOUT,
        "mae": fila_mae["mae"],
        "mape": fila_mae["mape"],
        "mae_estacional": next(c["mae"] for c in comparacion if c["modelo"] == "estacional"),
        "supera_estacional": ganador != "estacional" and maes[ganador] < maes["estacional"],
        "empate_simple": ganador != mas_fino,
        "modelo_mas_fino": mas_fino,
        "banda": banda,
        "comparacion": comparacion,
        "historico": hist,
        "pronostico": puntos,
        "reparados": reparados,
        "n_observado": len(periodos),
        "notas": notas,
    }


def frase_resumen(series):
    cuentas = {nombre: 0 for nombre in ORDEN}
    for serie in series:
        cuentas[serie["modelo"]] += 1
    partes = []
    for nombre in ORDEN:
        n = cuentas[nombre]
        if not n:
            continue
        partes.append(f"«{ETIQUETAS[nombre]}» en {n} serie" + ("s" if n != 1 else ""))
    estacionales = [s for s in series if s["modelo"] == "estacional"]
    if not estacionales:
        cierre = "Todas mejoran al repetir el mismo mes del año anterior."
    else:
        bits = []
        for serie in estacionales:
            if serie.get("empate_simple"):
                bits.append(
                    f"{serie['nombre']}: «{ETIQUETAS[serie['modelo_mas_fino']]}» quedó a menos del 2 % "
                    "y se deja el mes anterior"
                )
            else:
                bits.append(f"{serie['nombre']}: el mes anterior tuvo el menor error")
        cierre = "No se reemplaza el mes del año anterior en " + "; ".join(bits) + "."
    return (
        f"Sobre las {len(series)} series mensuales, el ensayo de {HOLDOUT} meses publica "
        + ", ".join(partes)
        + ". "
        + cierre
    )


DESCARTADOS = [
    "Red neuronal: las series tienen entre 54 y 96 meses. No alcanza para un modelo profundo.",
    "Operaciones aéreas (31 meses), BTS T-100 (24) e IPC nacional (33) se quedan cortos para un ensayo de 6 meses y una estacionalidad de 12.",
    "El agregado de países es anual. No se inventan meses.",
    "OWID Colombia es anual y en esta descarga corta en 2022.",
    "SISAIRE tiene 11 días y cierra en 2025-12-31.",
    "La TRM oficial publicada es una ventana de días, no una serie de este horizonte.",
    "La lluvia del corte es un mes y la EVI es una ola semestral.",
    "Llegadas por país del archivo anual y el benchmark europeo no entran: otro grano, u otra pregunta.",
]


def construir(crudas):
    libs = _librerias()
    series = []
    for spec in crudas["specs"]:
        fila = construir_serie(spec, crudas["periodos"][spec["id"]], crudas["valores"][spec["id"]], libs)
        if fila:
            series.append(fila)
    cortes = [s["corte"] for s in series]
    return {
        "id": "bureau-pronostico",
        "estado": "ok" if series else "skip",
        "titulo": "Pronóstico a 6 meses",
        "generado": max(cortes) if cortes else "",
        "horizonte_meses": HORIZONTE,
        "holdout_meses": HOLDOUT,
        "fuente": "Aerocivil (cinco mercados), EMA Antioquia (ocupación y tarifa) y SIEDCO Medellín (homicidios y hurtos).",
        "resumen": {
            "n": len(series),
            "por_modelo": {nombre: sum(1 for s in series if s["modelo"] == nombre) for nombre in ORDEN},
            "superan_estacional": sum(1 for s in series if s["supera_estacional"]),
            "frase": frase_resumen(series) if series else "Sin series.",
        },
        "fuera": (
            "No se modelan una red neuronal ni las series cortas o de otro grano: "
            "operaciones aéreas, BTS, IPC, OWID, SISAIRE, TRM y EVI."
        ),
        "descartados": DESCARTADOS,
        "series": series,
    }


def _periodo(anio, mes):
    return f"{int(anio):04d}-{int(mes):02d}"


def _specs():
    def llegadas(mercado, nombre):
        return {
            "id": "llegadas_" + _slug(mercado),
            "tab": "mercados",
            "nombre": nombre,
            "unidad": "pasajeros",
            "decimales": 0,
            "piso": 0,
            "techo": None,
            "caer_ceros": False,
            "notas": [
                f"Llegadas Aerocivil realizadas del mercado {mercado}. No son reservas ni el cupo de un aeropuerto.",
            ],
        }

    mercados = [
        ("Colombia", "Llegadas desde Colombia"),
        ("Estados Unidos", "Llegadas desde Estados Unidos"),
        ("México", "Llegadas desde México"),
        ("Brasil", "Llegadas desde Brasil"),
        ("Europa", "Llegadas desde Europa"),
    ]
    specs = [llegadas(m, n) for m, n in mercados]
    specs.append({
        "id": "llegadas_cinco",
        "tab": "mercados",
        "nombre": "Llegadas de los cinco mercados",
        "unidad": "pasajeros",
        "decimales": 0,
        "piso": 0,
        "techo": None,
        "caer_ceros": False,
        "notas": [
            "Suma de Brasil, Colombia, Estados Unidos, Europa y México. "
            "Brasil en 2022-05 entra corregido, no con la llegada de 1 pasajero.",
        ],
    })
    specs.append({
        "id": "ocupacion_antioquia",
        "tab": "visitante",
        "nombre": "Ocupación hotelera de Antioquia",
        "unidad": "%",
        "decimales": 2,
        "piso": 0,
        "techo": 100,
        "caer_ceros": False,
        "notas": ["Ocupación de la región Antioquia en la EMA. No es la ciudad de Medellín ni un hotel."],
    })
    specs.append({
        "id": "tarifa_antioquia",
        "tab": "visitante",
        "nombre": "Índice de tarifa hotelera de Antioquia",
        "unidad": "índice",
        "decimales": 2,
        "piso": 0,
        "techo": None,
        "caer_ceros": False,
        "notas": ["Índice de tarifa de Antioquia en la EMA. No es el IPC nacional ni la tarifa de un hotel."],
    })
    specs.append({
        "id": "homicidios",
        "tab": "visitante",
        "nombre": "Homicidios en Medellín",
        "unidad": "casos",
        "decimales": 0,
        "piso": 0,
        "techo": None,
        "caer_ceros": True,
        "notas": ["Casos mensuales SIEDCO en la ciudad. No es una tasa por habitante."],
    })
    specs.append({
        "id": "hurtos",
        "tab": "visitante",
        "nombre": "Hurtos en Medellín",
        "unidad": "casos",
        "decimales": 0,
        "piso": 0,
        "techo": None,
        "caer_ceros": False,
        "notas": ["Hurtos mensuales SIEDCO en la ciudad. No es una tasa por habitante ni está partido por zona."],
    })
    return specs


def _slug(mercado):
    return {
        "Colombia": "colombia",
        "Estados Unidos": "estados_unidos",
        "México": "mexico",
        "Brasil": "brasil",
        "Europa": "europa",
    }[mercado]


def _sumar(mapas):
    comunes = set(mapas[0])
    for mapa in mapas[1:]:
        comunes &= set(mapa)
    periodos = sorted(comunes)
    valores = [float(sum(mapa[p] for mapa in mapas)) for p in periodos]
    return periodos, valores


def leer_vivo():
    raiz = os.environ.get("TABLEROS_ROOT")
    candidatos = []
    if raiz:
        candidatos.append(Path(raiz))
    candidatos.append(Path("/tmp/tableros-bureau"))
    abierto = None
    for cand in candidatos:
        if (cand / "data" / "open" / "conectividad.json").exists() and (cand / "data" / "open" / "ema.json").exists():
            abierto = cand / "data" / "open"
            break
    if abierto is None or not SEGURIDAD.exists():
        return None
    con = json.loads((abierto / "conectividad.json").read_text(encoding="utf-8"))
    ema = json.loads((abierto / "ema.json").read_text(encoding="utf-8"))
    seg = json.loads(SEGURIDAD.read_text(encoding="utf-8"))
    por_mercado = {}
    for fila in con.get("serie") or []:
        por_mercado.setdefault(fila["mercado"], []).append(fila)
    periodos = {}
    valores = {}
    mapas = []
    for mercado in ("Colombia", "Estados Unidos", "México", "Brasil", "Europa"):
        filas = sorted(por_mercado.get(mercado) or [], key=lambda r: (r["anio"], r["mes"]))
        p = [_periodo(r["anio"], r["mes"]) for r in filas]
        v = [float(r["llegadas"]) for r in filas]
        periodos["llegadas_" + _slug(mercado)] = p
        valores["llegadas_" + _slug(mercado)] = v
        corregidos, _ = reparar(v)
        mapas.append({per: val for per, val in zip(p, corregidos)})
    p5, v5 = _sumar(mapas)
    periodos["llegadas_cinco"] = p5
    valores["llegadas_cinco"] = v5
    oc = ema["ocupacion"]["serie"]
    periodos["ocupacion_antioquia"] = [_periodo(r["anio"], r["mes"]) for r in oc]
    valores["ocupacion_antioquia"] = [float(r["antioquia"]) for r in oc]
    tar = ema["serie"]
    periodos["tarifa_antioquia"] = [_periodo(r["anio"], r["mes"]) for r in tar]
    valores["tarifa_antioquia"] = [float(r["indice_antioquia"]) for r in tar]
    sm = seg["serie_mensual"]
    periodos["homicidios"] = [r["periodo"] for r in sm]
    valores["homicidios"] = [float(r["homicidios"]) for r in sm]
    periodos["hurtos"] = [r["periodo"] for r in sm]
    valores["hurtos"] = [float(r["hurtos"]) for r in sm]
    return {"specs": _specs(), "periodos": periodos, "valores": valores}


def guardar_insumos(crudas, path=INSUMOS):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "specs": crudas["specs"],
        "periodos": crudas["periodos"],
        "valores": crudas["valores"],
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def leer_slim(path=INSUMOS):
    if not path.exists():
        raise FileNotFoundError(str(path))
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["valores"] = {k: [float(v) for v in vals] for k, vals in doc["valores"].items()}
    return doc


def cargar():
    vivo = leer_vivo()
    if vivo and len(vivo["periodos"]) >= 8:
        return vivo
    slim = leer_slim()
    slim["specs"] = _specs()
    return slim


def run():
    try:
        doc = construir(cargar())
        if not doc["series"]:
            print("[pronostico] sin series")
            return {"status": "skip", "motivo": "sin series"}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
        if OUT.exists() and OUT.read_text(encoding="utf-8") == texto:
            print(f"[pronostico] sin cambios ({len(doc['series'])} series)")
            return {"status": "ok", "n": len(doc["series"]), "cambio": False}
        OUT.write_text(texto, encoding="utf-8")
        print(f"[pronostico] {len(doc['series'])} series -> {OUT.name}")
        return {"status": "ok", "n": len(doc["series"])}
    except Exception as exc:
        print(f"[pronostico][SKIP] {exc}")
        return {"status": "skip", "motivo": str(exc)[:200]}


if __name__ == "__main__":
    vivo = leer_vivo()
    if vivo:
        guardar_insumos(vivo)
        print(f"[pronostico] insumos {INSUMOS.name}")
    raise SystemExit(0 if run().get("status") == "ok" else 1)
