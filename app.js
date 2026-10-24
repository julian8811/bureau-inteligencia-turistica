(function () {
  "use strict";

  var state = {
    tab: "mercados",
    anio: 2025,
    pais: "Todos",
    ficha: null,
    volverFicha: "",
    calc: { inspecciones: "", confirmadas: "", stockInicial: "", cuota: "", anos: "" }
  };

  var PAIS_DE_MERCADO = { Colombia: "COLOMBIA", "Estados Unidos": "ESTADOS UNIDOS", "México": "MEXICO", Brasil: "BRASIL" };
  var CIUDAD_DE_PAIS = {
    PANAMA: "Ciudad de Panamá",
    "REPUBLICA DOMINICANA": "Santo Domingo",
    ECUADOR: "Quito",
    ARGENTINA: "Buenos Aires",
    CHILE: "Santiago",
    ESPANA: "Madrid",
    PERU: "Lima",
    COLOMBIA: "Medellín",
    MEXICO: "Ciudad de México",
    BRASIL: "São Paulo"
  };

  var DATA = {};
  var MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  var MERCADOS = ["Colombia", "Estados Unidos", "México", "Brasil", "Europa"];
  var DESTINOS = ["Medellín", "Bogotá", "Cartagena", "Ciudad de México", "São Paulo", "Lima"];
  var COLOR = {
    Colombia: "#172139", "Estados Unidos": "#E9901E", "México": "#108181", Brasil: "#B4C42C", Europa: "#195855",
    MDE: "#108181", EOH: "#E9901E", CENTRO: "#172139", LAURELES: "#108181", POBLADO: "#E9901E"
  };

  function esc(text) {
    return String(text == null ? "" : text).replace(/[&<>"]/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
    });
  }

  function num(value, digits) {
    if (value == null || isNaN(value)) return "—";
    return Number(value).toLocaleString("es-CO", { maximumFractionDigits: digits == null ? 0 : digits, minimumFractionDigits: digits == null ? 0 : digits });
  }

  function pesos(value) {
    if (value == null) return "—";
    return "$" + num(value, 0);
  }

  function usd(value) {
    if (value == null) return "—";
    return "USD " + num(value, value >= 100 ? 0 : 2);
  }

  function pastilla(id) {
    var ficha = window.fichaPorId(id);
    return '<span class="pastilla ' + ficha.clase + '">' + esc(ficha.pastilla) + "</span>";
  }

  function kpi(id, label, value, meta) {
    return '<article class="kpi"><button class="hit" type="button" data-ficha="' + id + '"><div class="label">' + esc(label) + '</div><div class="value">' + value + '</div><div class="meta">' + pastilla(id) + (meta ? " · " + esc(meta) : "") + "</div></button></article>";
  }

  function block(title, hint, body) {
    return '<section class="block"><h3>' + esc(title) + '</h3>' + (hint ? '<span class="hint">' + hint + "</span>" : "") + body + "</section>";
  }

  function grupo(titulo, celdas) {
    return '<section class="grupo"><h2>' + esc(titulo) + '</h2><div class="lienzo">' + celdas + "</div></section>";
  }

  function celda(clase, html) {
    return '<div class="' + clase + '">' + html + "</div>";
  }

  function hueco(titulo, texto) {
    return '<div class="hueco"><strong>' + esc(titulo) + "</strong><p>" + texto + "</p></div>";
  }

  function notaSim(supuesto) {
    return '<p class="nota-sim"><span class="pastilla simulacion">Simulación</span> Simulación. No es una cifra del Bureau ni de una base abierta. Supuesto: ' + supuesto + "</p>";
  }

  function fold(text) {
    return String(text || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/\s+/g, " ").trim();
  }

  function etiquetaPais(pais) {
    if (!pais || pais === "Todos") return "Todos";
    return String(pais).toLowerCase().replace(/(^|\s)\S/g, function (letra) { return letra.toUpperCase(); });
  }

  function mercadoDe(pais) {
    if (!pais || pais === "Todos") return "";
    var fila = ((DATA.conectividad && DATA.conectividad.paises) || []).find(function (row) {
      return row.pais === pais && row.mercado;
    });
    return fila ? fila.mercado : "";
  }

  function leerUrl() {
    var q = new URLSearchParams(location.search);
    var tabs = ["mercados", "visitante", "captacion", "miembros"];
    if (tabs.indexOf(q.get("tab")) >= 0) state.tab = q.get("tab");
    var anio = Number(q.get("anio"));
    if (anio) state.anio = anio;
    if (q.get("pais")) state.pais = q.get("pais");
  }

  function escribirUrl() {
    var q = new URLSearchParams();
    q.set("tab", state.tab);
    q.set("anio", String(state.anio));
    q.set("pais", state.pais);
    var siguiente = "?" + q.toString();
    if (location.search !== siguiente) history.replaceState({ tab: state.tab, anio: state.anio, pais: state.pais }, "", siguiente);
  }

  function filasAnio(serie, anio) {
    return (serie || []).filter(function (row) { return row.anio === anio; });
  }

  function trimestre(mes) {
    return Math.floor((mes - 1) / 3) + 1;
  }

  function olaPara(anio) {
    var olas = (DATA.evi && DATA.evi.olas) || [];
    var nombre = anio <= 2024 ? "Agosto 2023 – julio 2024" : "Enero – junio 2025";
    var hallada = olas.find(function (ola) { return ola.ola === nombre; });
    if (hallada) return { ola: hallada, aviso: anio >= 2026 ? "Última ola publicada. 2026 no tiene microdato en el catálogo 869." : "" };
    if (olas.length) return { ola: olas[olas.length - 1], aviso: "Se muestra la última ola publicada." };
    return { ola: null, aviso: "" };
  }

  function sumaMercado(filas, campo) {
    var cubo = {};
    MERCADOS.forEach(function (m) { cubo[m] = 0; });
    filas.forEach(function (row) {
      if (cubo[row.mercado] != null) cubo[row.mercado] += row[campo] || 0;
    });
    return cubo;
  }

  function puntosMes(filas, campo, mercado) {
    var puntos = [];
    for (var mes = 1; mes <= 12; mes++) {
      var y = filas.filter(function (row) {
        return row.mes === mes && (!mercado || row.mercado === mercado);
      }).reduce(function (s, row) { return s + (row[campo] || 0); }, 0);
      if (y) puntos.push({ x: MESES[mes - 1], y: y });
    }
    return puntos;
  }

  function rankingPaises() {
    var filas = filasAnio(DATA.conectividad.paises || [], state.anio);
    var cubo = {};
    filas.forEach(function (row) {
      if (!cubo[row.pais]) cubo[row.pais] = { pais: row.pais, llegadas: 0, priorizado: false, mercado: row.mercado || "" };
      cubo[row.pais].llegadas += row.llegadas || 0;
      if (row.priorizado) cubo[row.pais].priorizado = true;
      if (row.mercado) cubo[row.pais].mercado = row.mercado;
    });
    return Object.keys(cubo).map(function (k) { return cubo[k]; }).sort(function (a, b) { return b.llegadas - a.llegadas; });
  }

  function vistaMercados() {
    var con = filasAnio(DATA.conectividad.serie, state.anio);
    var ema = filasAnio(DATA.ema.serie, state.anio);
    var ultimo = ema[ema.length - 1];
    var totalP;
    var totalL;
    var movimiento;
    var titulo;
    var pista;
    if (state.pais === "Todos") {
      var pasajeros = sumaMercado(con, "pasajeros");
      var llegadas = sumaMercado(con, "llegadas");
      totalP = MERCADOS.reduce(function (s, m) { return s + (pasajeros[m] || 0); }, 0);
      totalL = MERCADOS.reduce(function (s, m) { return s + (llegadas[m] || 0); }, 0);
      movimiento = Charts.multiLine(MERCADOS.map(function (m) {
        return { name: m, color: COLOR[m], pais: PAIS_DE_MERCADO[m] || "", points: puntosMes(con, "pasajeros", m) };
      }).filter(function (s) { return s.points.length; }));
      titulo = "Pasajeros por mercado y mes";
      pista = "Aerocivil. Los cinco mercados de la lista. Un clic en el punto elige el país.";
    } else {
      var delPais = filasAnio(DATA.conectividad.paises || [], state.anio).filter(function (row) { return row.pais === state.pais; });
      totalP = delPais.reduce(function (s, row) { return s + (row.pasajeros || 0); }, 0);
      totalL = delPais.reduce(function (s, row) { return s + (row.llegadas || 0); }, 0);
      var fichaPais = delPais[0] || {};
      movimiento = Charts.stacked([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(function (mes) {
        var fila = delPais.filter(function (row) { return row.mes === mes; })[0] || {};
        return {
          label: MESES[mes - 1],
          pais: state.pais,
          parts: [
            { name: "Llegadas", value: fila.llegadas || 0, color: "#E9901E", pais: state.pais },
            { name: "Salidas", value: fila.salidas || 0, color: "#108181", pais: state.pais }
          ]
        };
      }).filter(function (item) { return item.parts[0].value || item.parts[1].value; }));
      titulo = "Llegadas y salidas";
      pista = "Aerocivil. " + etiquetaPais(state.pais) + (fichaPais.priorizado ? " · lista Bureau" + (fichaPais.mercado ? " · " + fichaPais.mercado : "") : " · fuera de la lista") + ".";
    }
    var html = '<div class="kpi-row">' +
      kpi("conectividad", "Pasajeros del año", num(totalP), state.pais === "Todos" ? "cinco mercados" : etiquetaPais(state.pais)) +
      kpi("reservas", "Llegadas del año", num(totalL), "realizadas, no reservas") +
      kpi("tarifas", "Antioquia vs regiones", ultimo ? num(ultimo.indice_100, 1) : "—", ultimo ? MESES[ultimo.mes - 1] + " " + state.anio : "sin corte") +
      kpi("icca", "Reuniones ICCA Medellín", "26", "puesto 103 · 2025") +
      "</div>";
    html += grupo("Conectividad", 
      celda("span-12", block(titulo, pista, movimiento || hueco("Sin mes", "Este año no tiene pasajeros de ese país en el agregado."))) +
      celda("span-7", otrosOrigenes()) +
      celda("span-5", aeropuertos()) +
      celda("span-7", aerolineas()) +
      celda("span-5", carga()));
    html += grupo("Destino y precios",
      celda("span-12", tarifas()) +
      celda("span-12", regionesOcupacion()) +
      celda("span-8", vozDigital()) +
      celda("span-4", icca()) +
      celda("span-12", medataFigura()));
    html += grupo("Simulación", celda("span-12", conversion()));
    return html;
  }

  function otrosOrigenes() {
    var top = rankingPaises().slice(0, 12);
    if (!top.length) return hueco("Países", "El agregado no trae la serie por país.");
    return block("Países con más llegadas", "Año " + state.anio + ". El clic deja el país en todo el tablero. Lista Bureau cuando el origen está priorizado.", Charts.bars(top.map(function (row) {
      return {
        label: etiquetaPais(row.pais),
        value: row.llegadas,
        text: num(row.llegadas),
        pais: row.pais,
        color: row.priorizado ? "#E9901E" : "#195855"
      };
    }), "#195855"));
  }

  function aeropuertos() {
    var filas = (DATA.conectividad.aeropuertos || []).filter(function (row) { return row.anio === state.anio; });
    var suma = {};
    filas.forEach(function (row) { suma[row.aeropuerto] = (suma[row.aeropuerto] || 0) + row.llegadas; });
    var items = Object.keys(suma).map(function (k) {
      return { label: k === "MDE" ? "Córdova" : "Olaya Herrera", value: suma[k], color: COLOR[k] || "#108181", text: num(suma[k]) };
    });
    return block("Llegadas por aeropuerto", items.length ? "Año " + state.anio + "." : "Corte pendiente.", items.length ? Charts.donut(items) : hueco("Sin corte", "Vuelva a correr el script de fuentes."));
  }

  function aerolineas() {
    var filas = (DATA.conectividad.aerolineas || []).filter(function (row) { return row.anio === state.anio; });
    return block("Aerolíneas con más llegadas", filas.length ? "Ocho primeras del año." : "Corte pendiente.", filas.length ? Charts.bars(filas.map(function (row) {
      return { label: row.sigla || row.nombre, value: row.llegadas, text: num(row.llegadas) };
    }), "#E9901E") : hueco("Sin corte", "Vuelva a correr el script de fuentes."));
  }

  function carga() {
    var filas = (DATA.conectividad.carga || []).filter(function (row) { return row.anio === state.anio; });
    var puntos = filas.map(function (row) { return { x: MESES[row.mes - 1], y: row.kg }; });
    return block("Carga y correo", "Kilos en vuelos que tocan MDE o EOH.", puntos.length ? Charts.line(puntos, "#195855") : hueco("Sin corte", "Vuelva a correr el script de fuentes."));
  }

  function medataFigura() {
    var serie = (DATA.medata && DATA.medata.serie) || [];
    var periodos = [];
    serie.forEach(function (row) {
      if (row.tar_periodo && periodos.indexOf(row.tar_periodo) < 0) periodos.push(row.tar_periodo);
    });
    periodos.sort();
    var grupos = periodos.slice(-6).map(function (periodo) {
      return {
        label: MESES[Number(periodo.slice(4)) - 1] + " " + periodo.slice(2, 4),
        bars: serie.filter(function (row) { return row.tar_periodo === periodo; }).map(function (row) {
          return { name: row.tar_zona, value: Number(row.tar_valor), color: COLOR[row.tar_zona] || "#108181" };
        })
      };
    });
    return block("Tarifa por zona", "Medata, pesos corrientes. La ficha se modificó el 14 de diciembre de 2023.", grupos.length ? Charts.grouped(grupos) : hueco("Medata", "Sin serie de zonas."));
  }

  function vozDigital() {
    var wiki = (DATA.wikipedia && DATA.wikipedia.serie) || [];
    var delAnio = wiki.filter(function (row) { return row.anio === state.anio; });
    var base = delAnio.filter(function (row) { return row.destino === "Medellín" && trimestre(row.mes) === 1; })
      .reduce(function (s, row) { return s + row.vistas; }, 0);
    var porDestino = {};
    delAnio.forEach(function (row) {
      var t = trimestre(row.mes);
      var key = row.destino + "-" + t;
      porDestino[key] = (porDestino[key] || 0) + row.vistas;
    });
    var destinos = DESTINOS.slice();
    delAnio.forEach(function (row) {
      if (destinos.indexOf(row.destino) < 0) destinos.push(row.destino);
    });
    var barras = destinos.map(function (destino, i) {
      var total = delAnio.filter(function (row) { return row.destino === destino; }).reduce(function (s, row) { return s + row.vistas; }, 0);
      return { label: destino, value: total, color: Charts.palette[i % Charts.palette.length], text: num(total) };
    }).filter(function (item) { return item.value; });
    var indice = "";
    if (base) {
      var puntos = [1, 2, 3, 4].map(function (t) {
        var vistas = porDestino["Medellín-" + t] || 0;
        return { x: "T" + t, y: Math.round(vistas / base * 100) };
      }).filter(function (p) { return p.y; });
      indice = Charts.line(puntos, "#108181", { mark: 100 });
    }
    var gdelt = (DATA.gdelt && DATA.gdelt.serie) || [];
    var gdAnio = gdelt.filter(function (row) { return row.anio === state.anio; });
    var sov = "";
    if (gdAnio.length) {
      var menciones = {};
      gdAnio.forEach(function (row) { menciones[row.destino] = (menciones[row.destino] || 0) + row.menciones; });
      sov = Charts.donut(Object.keys(menciones).map(function (k, i) {
        return { label: k, value: menciones[k], color: Charts.palette[i], text: num(menciones[k]) };
      }));
    } else {
      sov = hueco("Share of voice de medios", "GDELT no entregó la línea de tiempo en esta descarga. La dona de arriba es la participación de vistas de Wikipedia.");
    }
    var ciudad = CIUDAD_DE_PAIS[state.pais];
    var notaCiudad = "";
    if (ciudad) {
      var vistasCiudad = delAnio.filter(function (row) { return row.destino === ciudad; }).reduce(function (s, row) { return s + row.vistas; }, 0);
      notaCiudad = vistasCiudad ? "<p class='hint'>Artículo asociado a " + esc(etiquetaPais(state.pais)) + ": " + esc(ciudad) + ", " + num(vistasCiudad) + " vistas en " + state.anio + ".</p>" : "";
    }
    return block("Interés digital", "Índice de Wikipedia de Medellín, base 100 en el primer trimestre de " + state.anio + ". GDELT, si falta, queda vacío.", (indice || "") + Charts.donut(barras) + notaCiudad + sov);
  }

  function tarifas() {
    var ema = filasAnio(DATA.ema.serie, state.anio);
    var linea = Charts.line(ema.map(function (row) { return { x: MESES[row.mes - 1], y: row.indice_100 }; }), "#108181", { mark: 100 });
    var ocup = DATA.ema && DATA.ema.ocupacion && DATA.ema.ocupacion.serie;
    var ocupAnio = filasAnio(ocup, state.anio);
    var ocupacion = "";
    if (ocupAnio.length) {
      ocupacion = Charts.multiLine([
        { name: "Antioquia", color: "#108181", points: ocupAnio.map(function (row) { return { x: MESES[row.mes - 1], y: row.antioquia }; }) },
        { name: "Bogotá", color: "#E9901E", points: ocupAnio.map(function (row) { return { x: MESES[row.mes - 1], y: row.bogota }; }) },
        { name: "Cartagena", color: "#FBBB28", points: ocupAnio.map(function (row) { return { x: MESES[row.mes - 1], y: row.cartagena }; }) }
      ]);
    }
    return block("Tarifa y ocupación", "La línea verde marca 100, el promedio regional del mes. La línea compara Antioquia, Bogotá y Cartagena.", linea + ocupacion);
  }

  function regionesOcupacion() {
    var ocup = DATA.ema && DATA.ema.ocupacion && DATA.ema.ocupacion.serie;
    var ocupAnio = filasAnio(ocup, state.anio);
    if (!ocupAnio.length || !ocupAnio[ocupAnio.length - 1].regiones) {
      return block("Ocupación regional", "Hoja 4.2.", hueco("Sin regiones", "El agregado todavía no trae las doce regiones."));
    }
    var corte = ocupAnio[ocupAnio.length - 1];
    var nombres = Object.keys(corte.regiones);
    return block("Ocupación de las regiones", "Porcentaje de la hoja 4.2 en " + MESES[corte.mes - 1] + " " + state.anio + ". Antioquia no es la ciudad de Medellín.", Charts.bars(nombres.map(function (nombre, i) {
      return { label: nombre, value: corte.regiones[nombre], text: num(corte.regiones[nombre], 1) + " %", color: Charts.palette[i % Charts.palette.length] };
    })));
  }

  function icca() {
    var colores = ["#E9901E", "#108181", "#172139"];
    var dona = Charts.donut(DATA.icca.ciudades.map(function (c, i) {
      return { label: c.ciudad, value: c.reuniones, color: colores[i], text: "puesto " + c.puesto };
    }));
    return block("ICCA 2025", "Reuniones elegibles de las tres ciudades citadas. No es la participación sobre el mundo.", dona + hueco("No ICCA", "UFI publica barómetros globales, no la participación de Medellín."));
  }

  function conversion() {
    var con = filasAnio(DATA.conectividad.serie, state.anio);
    var llegadas = sumaMercado(con, "llegadas");
    var total = MERCADOS.reduce(function (s, m) { return s + (llegadas[m] || 0); }, 0) || 1;
    var items = MERCADOS.map(function (m) {
      var parte = (llegadas[m] || 0) / total * 100;
      return { label: m, value: parte, text: num(parte, 1) + " %", sim: true, pais: PAIS_DE_MERCADO[m] || "" };
    });
    return block("Peso de llegadas entre mercados", pastilla("conversion"), Charts.bars(items, Charts.SIM) + notaSim("se reparte el peso de las llegadas Aerocivil de " + state.anio + " entre los cinco mercados. No es la tasa del CRM."));
  }

  function vistaVisitante() {
    var paquete = olaPara(state.anio);
    var ola = paquete.ola;
    if (!ola) {
      return hueco("EVI", "El agregado de la encuesta no tiene olas. Vuelva a correr el script de fuentes.");
    }
    var gastoPais = (ola.gasto_por_pais || []).find(function (row) { return fold(row.pais) === state.pais; });
    var mercado = mercadoDe(state.pais);
    var gastoMercado = (ola.gasto_por_mercado || []).find(function (row) { return row.mercado === mercado; });
    var gasto = gastoPais ? gastoPais.gasto_estadia_usd : (gastoMercado ? gastoMercado.gasto_estadia_usd : ola.gasto_estadia_usd);
    var gastoMeta = state.pais === "Todos" ? "todos los orígenes" : (gastoPais ? etiquetaPais(state.pais) : (gastoMercado ? mercado : "todos los orígenes"));
    var huella = ((DATA.huella && DATA.huella.serie) || []).find(function (row) { return row.ola === ola.ola; });
    var html = "";
    if (paquete.aviso || state.anio !== 2025) {
      html += '<p class="aviso">Ola mostrada en las composiciones: ' + esc(ola.ola) + ". " + esc(paquete.aviso) + "</p>";
    }
    var meses = ((DATA.evi && DATA.evi.meses) || []).filter(function (row) { return row.anio === state.anio; });
    var movimiento = meses.length ? Charts.line(meses.map(function (row) {
      return { x: MESES[row.mes - 1], y: row.gasto_estadia_usd };
    }), "#FBBB28") : hueco("Sin mes", "El agregado todavía no trae la serie mensual. Las composiciones usan la ola.");
    html += '<div class="kpi-row">' +
      kpi("gasto", "Gasto de la estadía", usd(gasto), gastoMeta) +
      kpi("gasto", "Gasto diario", state.pais === "Todos" ? usd(ola.gasto_diario_usd) : "—", state.pais === "Todos" ? "por persona" : "el diario no está partido por país") +
      kpi("grupo", "Noches del destino principal", num(ola.noches, 1), "n ponderada " + num(ola.n_noches, 0)) +
      kpi("huella", "Huella estimada", huella && huella.kg_total != null ? num(huella.kg_total, 1) + " kg" : "—", "ida + alojamiento") +
      "</div>";
    html += grupo("Estadía",
      celda("span-12", block("Gasto mensual de la estadía", "Promedio ponderado de los no residentes en José María Córdova. " + state.anio + ".", movimiento)) +
      celda("span-6", block("Grupo de viaje", "Ponderado con el factor de expansión. n de encuestas: " + num(ola.n) + ".", Charts.donut((ola.grupo || []).map(function (g, i) {
        return { label: g.nombre, value: g.participacion, color: Charts.palette[i], text: num(g.participacion, 1) + "%" };
      })))) +
      celda("span-6", block("Motivo del viaje", "Ola completa.", Charts.donut((ola.motivos || []).map(function (g, i) {
        return { label: g.nombre, value: g.participacion, color: Charts.palette[i], text: num(g.participacion, 1) + "%" };
      })))) +
      celda("span-12", block("Residencia", "Países con al menos 0,5 % del peso de la ola. Un clic los selecciona.", Charts.bars((ola.residencia || []).map(function (g) {
        var codigo = fold(g.nombre);
        return { label: g.nombre, value: g.participacion, text: num(g.participacion, 1) + "%", pais: codigo, color: codigo === state.pais ? "#172139" : "#108181" };
      }), "#108181"))));
    html += grupo("Huella y escenario",
      celda("span-6", compararOlas()) +
      celda("span-6", huellaBloque(huella, ola)) +
      celda("span-12", npsSimulado()));
    return html;
  }

  function npsSimulado() {
    var promotores = 46;
    var pasivos = 34;
    var detractores = 20;
    var nps = promotores - detractores;
    return block("Satisfacción y NPS", pastilla("nps"), Charts.columns([
      { label: "Promotores", value: promotores, text: String(promotores), sim: true },
      { label: "Pasivos", value: pasivos, text: String(pasivos), sim: true },
      { label: "Detractores", value: detractores, text: String(detractores), sim: true }
    ]) + "<p class='hint'>NPS del escenario: " + nps + ".</p>" + notaSim("46 promotores, 34 pasivos y 20 detractores de ejemplo. No usa el 4,9 de miembros ni la pregunta de recomendación de la EVI."));
  }

  function compararOlas() {
    var olas = (DATA.evi && DATA.evi.olas) || [];
    if (olas.length < 2) return block("Olas", "Hace falta más de una ola para comparar.", "");
    return block("Gasto de las dos olas", "USD por persona. Cada barra es su propia ola, no un mes.", Charts.bars(olas.map(function (ola, i) {
      return { label: ola.ola, value: ola.gasto_estadia_usd, text: usd(ola.gasto_estadia_usd), color: i ? "#FBBB28" : "#E9901E" };
    })));
  }

  function huellaBloque(huella, ola) {
    if (!huella || huella.kg_total == null) {
      var estado = (DATA.huella && DATA.huella.estado) || "Sin factores.";
      return block("Huella", pastilla("huella"), hueco("Sin estimación", esc(estado) + " Las noches de la ola sí están en la tarjeta de estadía: " + num(ola.noches, 1) + "."));
    }
    var aire = DATA.huella && DATA.huella.factores && DATA.huella.factores.aereo_kg_por_pasajero_km;
    var hotel = DATA.huella && DATA.huella.factores && DATA.huella.factores.hotel_kg_por_noche;
    var factores = aire && hotel ? " Factores: " + num(aire.factor, 5) + " kg por pasajero·km y " + num(hotel.factor, 1) + " kg por noche." : "";
    return block("Huella de la ola", "Tramo de ida. " + num(huella.km_ida, 0) + " km medios." + factores, Charts.bars([
      { label: "Vuelo", value: huella.kg_vuelo, text: num(huella.kg_vuelo, 1) + " kg" },
      { label: "Alojamiento", value: huella.kg_alojamiento, text: num(huella.kg_alojamiento, 1) + " kg" }
    ], "#195855"));
  }

  function vistaCaptacion() {
    var inf = window.INFORME;
    var aporteEvento = inf.impactoUsd / inf.captados;
    var aporteAsistente = inf.impactoUsd / inf.asistentes;
    var html = "";
    if (state.anio !== 2025) html += '<p class="aviso">El informe citado es el corte 2025. El filtro de año no fabrica otro corte.</p>';
    html += '<div class="stocks">' + inf.flujo.map(function (item) {
      return '<article class="stock"><div class="k">' + esc(item.etiqueta) + '</div><div class="v">' + esc(item.valor) + '</div><p>' + esc(item.detalle || item.universo) + "</p></article>";
    }).join("") + "</div>";
    html += '<p class="hint mt">Tres stocks de universos distintos. No hay tasa entre ellos: los captados superan a las candidaturas.</p>';
    html += '<div class="kpi-row mt">' +
      kpi("roi", "Aporte por evento", usd(aporteEvento), "156.168.654 / 103") +
      kpi("roi", "Aporte por asistente", usd(aporteAsistente), "sobre 242.019 proyectados") +
      kpi("roi", "Cuartos noche", num(inf.cuartosNoche), "publicados con los 103") +
      kpi("flujo", "Internacionales", num(inf.internacionales), "de 103 captados y apoyados") +
      "</div>";
    html += grupo("Captados",
      celda("span-12", prioridad()) +
      celda("span-5", block("Dentro de los 103", "59 internacionales y 44 nacionales. Los dólares no se reparten.", Charts.donut([
        { label: "Internacionales", value: inf.internacionales, color: "#108181", text: String(inf.internacionales) },
        { label: "Nacionales", value: inf.nacionales, color: "#E9901E", text: String(inf.nacionales) }
      ]))) +
      celda("span-7", costoSimulado(aporteEvento)) +
      celda("span-12", calculadoraInspeccion()));
    html += grupo("Después de la candidatura",
      celda("span-7", perdidas()) +
      celda("span-5", block("Eventos realizados", "Otro universo. No se suma al flujo de captación.", "<p>Medellín recibió <strong>" + num(inf.realizados.eventos) + "</strong> eventos, con " + num(inf.realizados.asistentes) + " asistentes y una derrama estimada de USD " + inf.realizados.derramaMillonesUsd + " millones.</p>")));
    return html;
  }

  function prioridad() {
    var con = filasAnio(DATA.conectividad.serie, state.anio === 2025 ? 2025 : state.anio);
    var pasajeros = sumaMercado(con, "pasajeros");
    var llegadas = sumaMercado(con, "llegadas");
    var paquete = olaPara(state.anio === 2026 ? 2025 : state.anio);
    var gasto = {};
    ((paquete.ola && paquete.ola.gasto_por_mercado) || []).forEach(function (row) { gasto[row.mercado] = row.gasto_estadia_usd; });
    function escala(mapa) {
      var max = Math.max.apply(null, MERCADOS.map(function (m) { return mapa[m] || 0; }).concat([1]));
      var out = {};
      MERCADOS.forEach(function (m) { out[m] = ((mapa[m] || 0) / max) * 100; });
      return out;
    }
    var a = escala(pasajeros), b = escala(llegadas), c = escala(gasto);
    var corto = { Colombia: "Colombia", "Estados Unidos": "EE. UU.", "México": "México", Brasil: "Brasil", Europa: "Europa" };
    var grupos = MERCADOS.map(function (m) {
      var codigo = PAIS_DE_MERCADO[m] || "";
      var activo = state.pais !== "Todos" && (state.pais === codigo || mercadoDe(state.pais) === m);
      return {
        label: corto[m],
        pais: activo ? state.pais : "",
        bars: [
          { name: "Pasajeros", value: a[m], color: "#E9901E", pais: activo ? state.pais : "" },
          { name: "Llegadas", value: b[m], color: "#108181", pais: activo ? state.pais : "" },
          { name: "Gasto EVI", value: c[m], color: "#FBBB28", pais: activo ? state.pais : "" }
        ]
      };
    });
    return block("Prioridad de mercado", "Cada barra va de 0 a 100 dentro de su componente. El índice usa 40 % pasajeros, 30 % llegadas y 30 % gasto EVI. Colombia no tiene gasto en esa encuesta. No es el scoring de organizadores.", Charts.grouped(grupos));
  }

  function costoSimulado(aporteEvento) {
    var costo = 250000;
    return block("Impacto y costo", pastilla("roi"), Charts.bars([
      { label: "Impacto por evento", value: aporteEvento, text: usd(aporteEvento), color: "#108181" },
      { label: "Costo supuesto", value: costo, text: "USD 250.000", sim: true }
    ], "#108181") + notaSim("una barra de costo de USD 250.000 por evento captado, al lado del impacto publicado. Los dólares no se parten entre los 59 internacionales y los 44 nacionales."));
  }

  function ejemploInspeccion() {
    return Charts.bars([
      { label: "Inspecciones", value: 10, text: "10", sim: true },
      { label: "Confirmaciones", value: 4, text: "4", sim: true }
    ], Charts.SIM) + notaSim("10 inspecciones y 4 confirmaciones escritas en esta tarjeta. La calculadora de abajo sigue en blanco al recargar.");
  }

  function calculadoraInspeccion() {
    var ins = Number(state.calc.inspecciones);
    var conf = Number(state.calc.confirmadas);
    var tasa = ins > 0 && state.calc.confirmadas !== "" ? conf / ins : null;
    return block("Visitas de inspección", pastilla("inspeccion") + ' <span class="pastilla usuario">Ejercicio del usuario</span>',
      ejemploInspeccion() +
      '<p class="hint">Candidaturas confirmadas después de la inspección, sobre inspecciones. El ejercicio no se guarda al recargar.</p>' +
      '<div class="calc"><label>Inspecciones<input data-calc="inspecciones" inputmode="numeric" value="' + esc(state.calc.inspecciones) + '"></label>' +
      '<label>Confirmadas<input data-calc="confirmadas" inputmode="numeric" value="' + esc(state.calc.confirmadas) + '"></label></div>' +
      '<p class="mt"><strong>' + (tasa == null ? "Sin cálculo" : num(tasa * 100, 1) + " %") + "</strong></p>");
  }

  function perdidas() {
    var motivos = ["Precio", "Fechas", "Recinto", "Conectividad", "Decisión de la asociación", "Otro"];
    return block("Motivos de pérdida", pastilla("perdidas"), Charts.bars(motivos.map(function (m) {
      return { label: m, value: 1, text: "parte igual", sim: true };
    }), Charts.SIM) + notaSim("la taxonomía publicada se reparte en partes iguales. No hay conteo de candidaturas perdidas."));
  }

  function vistaMiembros() {
    var inf = window.INFORME;
    var r = inf.rueda;
    var porCita = r.expectativa / r.citas;
    var porRueda = r.expectativa / r.miembros;
    var porActivo = r.expectativa / inf.miembros;
    var participacion = r.miembros / inf.miembros;
    var efectividad = r.cumplieron / r.citas;
    var altas = inf.altas / inf.miembros;
    var html = "";
    if (state.anio !== 2025) html += '<p class="aviso">El informe citado es el corte 2025.</p>';
    html += '<div class="kpi-row">' +
      kpi("oportunidades", "Expectativa por cita", pesos(porCita), "7.925.390.000 / 433") +
      kpi("oportunidades", "Expectativa por miembro de la rueda", pesos(porRueda), "entre 68 participantes") +
      kpi("engagement", "Participación en la rueda", num(participacion * 100, 1) + " %", "68 / 200") +
      kpi("satisfaccion", "Satisfacción de la gestión", num(inf.satisfaccion, 1) + " / " + inf.satisfaccionEscala, "n no publicada") +
      "</div>";
    html += grupo("Rueda y padrón",
      celda("span-5", block("Citas de la rueda", "418 cumplieron expectativas y 15 no, sobre las mismas 433 citas. El informe redondea la efectividad a 96,5 %.", Charts.donut([
        { label: "Cumplieron", value: r.cumplieron, color: "#108181", text: String(r.cumplieron) },
        { label: "No cumplieron", value: r.citas - r.cumplieron, color: "#FBBB28", text: String(r.citas - r.cumplieron) }
      ]))) +
      celda("span-7", block("Padrón de la rueda", "68 de los 200 activos fueron a la rueda. El resto del padrón no es deserción.", Charts.bars([
        { label: "En la rueda", value: r.miembros, text: String(r.miembros), color: "#00AEAC" },
        { label: "Activos sin rueda", value: inf.miembros - r.miembros, text: String(inf.miembros - r.miembros), color: "#172139" }
      ]))) +
      celda("span-6", block("Padrón", pastilla("retencion"), "<ul class='lista'><li><span>Activos al cierre</span><strong>" + inf.miembros + "</strong></li><li><span>Altas del año</span><strong>" + inf.altas + "</strong></li><li><span>Altas sobre el cierre</span><strong>" + num(altas * 100, 1) + " %</strong></li></ul><p class='hint'>23 / 200 no es la deserción. Falta el padrón de apertura.</p><p>Segmentos de las altas, sin conteo: " + esc(inf.segmentosAltas.join(", ")) + ".</p>")) +
      celda("span-6", block("Expectativa del año", "Dos denominadores publicados. No es el valor de vida.", "<ul class='lista'><li><span>Por cita</span><strong>" + pesos(porCita) + "</strong></li><li><span>Por quien fue a la rueda</span><strong>" + pesos(porRueda) + "</strong></li><li><span>Por activo</span><strong>" + pesos(porActivo) + "</strong></li></ul>")));
    html += grupo("Ejercicio y simulación",
      celda("span-6", calculadoraMiembros()) +
      celda("span-6", vidaSimulada()) +
      celda("span-12", confianzaSimulada()));
    return html;
  }

  function vidaSimulada() {
    var apertura = 190;
    var cuota = 2400000;
    var anos = 4;
    var bajas = apertura + window.INFORME.altas - window.INFORME.miembros;
    var desercion = bajas / apertura * 100;
    var vida = cuota * anos;
    return block("Valor de vida y deserción", pastilla("valor"), Charts.bars([
      { label: "Deserción del ejemplo", value: desercion, text: num(desercion, 1) + " %", sim: true }
    ], Charts.SIM) + "<p class='hint'>Valor de vida del ejemplo: " + pesos(vida) + ".</p>" + notaSim("un padrón de apertura de 190, una cuota de $2.400.000 y 4 años. 23 sobre 200 no es la deserción."));
  }

  function confianzaSimulada() {
    return block("Confianza", pastilla("satisfaccion"), Charts.columns([
      { label: "Satisfacción", value: window.INFORME.satisfaccion, text: "4,9", color: "#108181" },
      { label: "Confianza", value: 3.2, text: "3,2", sim: true }
    ]) + notaSim("una segunda marca en 3,2 sobre la escala de 1 a 5. El 4,9 sigue como satisfacción publicada."));
  }

  function calculadoraMiembros() {
    var stock = Number(state.calc.stockInicial);
    var cuota = Number(state.calc.cuota);
    var anos = Number(state.calc.anos);
    var bajas = state.calc.stockInicial === "" ? null : stock + window.INFORME.altas - window.INFORME.miembros;
    var desercion = stock > 0 && bajas != null && bajas >= 0 ? bajas / stock : null;
    var ltv = cuota > 0 && anos > 0 ? cuota * anos : null;
    var notaBajas = "";
    if (bajas != null && bajas < 0) notaBajas = "<p class='hint'>Ese padrón de apertura no cierra con 23 altas y 200 activos.</p>";
    return block("Deserción y valor de vida", '<span class="pastilla usuario">Ejercicio del usuario</span>',
      '<p class="hint">Bajas = padrón de apertura + 23 − 200. Valor de vida de ejercicio = cuota × años. Se borra al recargar.</p>' +
      '<div class="calc"><label>Padrón al abrir 2025<input data-calc="stockInicial" inputmode="numeric" value="' + esc(state.calc.stockInicial) + '"></label>' +
      '<label>Cuota anual<input data-calc="cuota" inputmode="numeric" value="' + esc(state.calc.cuota) + '"></label>' +
      '<label>Años<input data-calc="anos" inputmode="numeric" value="' + esc(state.calc.anos) + '"></label></div>' +
      "<p class='mt'><strong>Deserción: " + (desercion == null ? "sin cálculo" : num(desercion * 100, 1) + " %") + "</strong></p>" + notaBajas +
      "<p><strong>Valor de vida de ejercicio: " + (ltv == null ? "sin cálculo" : pesos(ltv)) + "</strong></p>");
  }

  function modal() {
    if (!state.ficha) return "";
    var ficha = window.fichaPorId(state.ficha);
    if (!ficha) return "";
    return '<div class="modal-back"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="ficha-titulo"><h3 id="ficha-titulo">' + esc(ficha.nombre) + "</h3><dl>" +
      "<dt>Fórmula</dt><dd>" + esc(ficha.formula) + "</dd>" +
      "<dt>Fuente</dt><dd>" + esc(ficha.fuenteTipo) + ". " + esc(ficha.fuente) + "</dd>" +
      "<dt>Periodicidad pedida</dt><dd>" + esc(ficha.pedida) + "</dd>" +
      "<dt>Grano real</dt><dd>" + esc(ficha.grano) + "</dd>" +
      "<dt>Unidad</dt><dd>" + esc(ficha.unidad) + "</dd>" +
      "<dt>Universo</dt><dd>" + esc(ficha.universo) + "</dd>" +
      "<dt>Licencia</dt><dd>" + esc(ficha.licencia) + "</dd>" +
      "<dt>Qué no mide</dt><dd>" + esc(ficha.noMide) + "</dd></dl>" +
      '<button class="btn mt" type="button" data-action="cerrar">Cerrar</button></div></div>';
  }

  function render() {
    Charts.setFoco(state.pais === "Todos" ? "" : state.pais);
    var preguntas = {
      mercados: ["¿Cómo se mueve la demanda de los mercados priorizados hacia Medellín?", "Pasajeros, interés digital, llegadas, ICCA y tarifas."],
      visitante: ["¿Quién llega, cuánto gasta, cuánto se queda y cómo evalúa el destino?", "Ola de la EVI en José María Córdova."],
      captacion: ["¿Qué organizadores avanzan, dónde se cae la candidatura y qué retorno deja cada segmento?", "Corte anual del informe de gestión 2025."],
      miembros: ["¿Cuánto vale, cuánto participa y cuánto se queda cada miembro?", "Rueda de Negocios y padrón publicados en 2025."]
    };
    var anos = [];
    (DATA.conectividad.serie || []).forEach(function (row) {
      if (anos.indexOf(row.anio) < 0) anos.push(row.anio);
    });
    anos.sort();
    var pregunta = preguntas[state.tab];
    var vista = { mercados: vistaMercados, visitante: vistaVisitante, captacion: vistaCaptacion, miembros: vistaMiembros }[state.tab]();
    var nombresTab = { mercados: "Mercados", visitante: "Visitante", captacion: "Captación B2B", miembros: "Miembros" };
    var ids = ["mercados", "visitante", "captacion", "miembros"];
    document.body.dataset.tablero = state.tab;
    document.getElementById("app").innerHTML =
      '<div class="mando"><div class="tabs" role="tablist" aria-label="Tableros">' + ids.map(function (id) {
        var activo = state.tab === id;
        return '<button type="button" role="tab" class="tab ' + id + (activo ? " active" : "") + '" id="tab-' + id + '" data-tab="' + id + '" aria-selected="' + activo + '" aria-controls="panel" tabindex="' + (activo ? "0" : "-1") + '">' + nombresTab[id] + "</button>";
      }).join("") + "</div>" +
      '<div class="filters"><label class="filter">Año<select data-filtro="anio">' + anos.map(function (anio) {
        return '<option' + (anio === state.anio ? " selected" : "") + ">" + anio + "</option>";
      }).join("") + '</select></label><label class="filter">País<select data-filtro="pais"><option value="Todos"' + (state.pais === "Todos" ? " selected" : "") + ">Todos</option>" +
      opcionesPais().map(function (row) {
        var marca = row.priorizado ? " · lista Bureau" : "";
        return '<option value="' + esc(row.pais) + '"' + (row.pais === state.pais ? " selected" : "") + ">" + esc(etiquetaPais(row.pais) + marca) + "</option>";
      }).join("") + "</select></label><span class='corte'>Agregados del " + esc((DATA.manifiesto && DATA.manifiesto.generado) || "—") + "</span></div></div>" +
      '<p class="qbox"><strong>' + esc(pregunta[0]) + "</strong><span>" + esc(pregunta[1]) + "</span></p>" +
      '<div id="panel" role="tabpanel" aria-labelledby="tab-' + state.tab + '">' + vista + "</div>" + modal();
    var estado = document.getElementById("estado");
    if (estado) estado.textContent = nombresTab[state.tab] + ", " + state.anio + ", " + etiquetaPais(state.pais);
    escribirUrl();
    if (state.ficha) {
      var cerrar = document.querySelector("[data-action='cerrar']");
      if (cerrar) cerrar.focus();
    } else if (state.volverFicha) {
      var origen = document.querySelector('[data-ficha="' + state.volverFicha + '"]');
      state.volverFicha = "";
      if (origen) origen.focus();
    }
  }

  function opcionesPais() {
    var lista = rankingPaises().slice(0, 20);
    if (state.pais !== "Todos" && !lista.some(function (row) { return row.pais === state.pais; })) {
      var extra = rankingPaises().find(function (row) { return row.pais === state.pais; });
      if (extra) lista.push(extra);
      else lista.push({ pais: state.pais, priorizado: !!mercadoDe(state.pais) });
    }
    return lista;
  }

  document.getElementById("app").addEventListener("click", function (event) {
    var tab = event.target.closest("[data-tab]");
    if (tab) { state.tab = tab.getAttribute("data-tab"); state.ficha = null; render(); return; }
    var pais = event.target.closest("[data-pais]");
    if (pais && pais.getAttribute("data-pais")) {
      state.pais = pais.getAttribute("data-pais");
      state.ficha = null;
      render();
      return;
    }
    var ficha = event.target.closest("[data-ficha]");
    if (ficha) {
      state.volverFicha = "";
      state.ficha = ficha.getAttribute("data-ficha");
      render();
      return;
    }
    if (event.target.closest("[data-action='cerrar']") || event.target.classList.contains("modal-back")) {
      state.volverFicha = state.ficha || "";
      state.ficha = null;
      render();
    }
  });

  document.getElementById("app").addEventListener("keydown", function (event) {
    var pestanas = ["mercados", "visitante", "captacion", "miembros"];
    if (event.target.closest && event.target.closest("[role='tab']") && (event.key === "ArrowRight" || event.key === "ArrowLeft")) {
      var indice = pestanas.indexOf(state.tab);
      var paso = event.key === "ArrowRight" ? 1 : -1;
      state.tab = pestanas[(indice + paso + pestanas.length) % pestanas.length];
      state.ficha = null;
      render();
      var siguiente = document.getElementById("tab-" + state.tab);
      if (siguiente) siguiente.focus();
      event.preventDefault();
      return;
    }
    if (!state.ficha) return;
    if (event.key === "Escape") {
      state.volverFicha = state.ficha;
      state.ficha = null;
      render();
      event.preventDefault();
      return;
    }
    if (event.key !== "Tab") return;
    var dialogo = document.querySelector(".modal");
    if (!dialogo) return;
    var focos = dialogo.querySelectorAll("button, a, input, select, textarea");
    if (!focos.length) return;
    var primero = focos[0];
    var ultimo = focos[focos.length - 1];
    if (event.shiftKey && document.activeElement === primero) {
      ultimo.focus();
      event.preventDefault();
    } else if (!event.shiftKey && document.activeElement === ultimo) {
      primero.focus();
      event.preventDefault();
    }
  });

  document.getElementById("app").addEventListener("change", function (event) {
    var filtro = event.target.getAttribute("data-filtro");
    if (filtro === "anio") state.anio = Number(event.target.value);
    if (filtro === "pais") state.pais = event.target.value;
    if (filtro) { state.ficha = null; render(); }
  });

  var tip = document.createElement("div");
  tip.id = "tip";
  tip.hidden = true;
  document.body.appendChild(tip);
  function mostrarTip(nodo) {
    if (!nodo) { tip.hidden = true; return; }
    tip.textContent = nodo.getAttribute("data-tip");
    tip.hidden = false;
    var caja = nodo.getBoundingClientRect();
    tip.style.left = Math.min(Math.max(8, caja.left), window.innerWidth - 240) + "px";
    tip.style.top = Math.min(caja.bottom + 8, window.innerHeight - 48) + "px";
  }
  document.addEventListener("mouseover", function (event) {
    var nodo = event.target.closest && event.target.closest("[data-tip]");
    if (!nodo) { tip.hidden = true; return; }
    mostrarTip(nodo);
  });
  document.addEventListener("mousemove", function (event) {
    if (tip.hidden) return;
    tip.style.left = Math.min(event.clientX + 14, window.innerWidth - 240) + "px";
    tip.style.top = (event.clientY + 18) + "px";
  });
  document.addEventListener("focusin", function (event) {
    var grafico = event.target.closest && event.target.closest(".marco");
    if (!grafico) return;
    mostrarTip(grafico.querySelector("[data-tip]"));
  });
  document.addEventListener("keydown", function (event) {
    var grafico = document.activeElement && document.activeElement.closest && document.activeElement.closest(".marco");
    if (!grafico || (event.key !== "ArrowRight" && event.key !== "ArrowLeft")) return;
    var puntos = grafico.querySelectorAll("[data-tip]");
    if (!puntos.length) return;
    var actual = Number(grafico.getAttribute("data-punto") || 0);
    var paso = event.key === "ArrowRight" ? 1 : -1;
    actual = (actual + paso + puntos.length) % puntos.length;
    grafico.setAttribute("data-punto", String(actual));
    mostrarTip(puntos[actual]);
    event.preventDefault();
  });

  document.getElementById("app").addEventListener("input", function (event) {
    var campo = event.target.getAttribute("data-calc");
    if (!campo) return;
    state.calc[campo] = event.target.value.replace(/[^\d]/g, "");
    render();
    var siguiente = document.querySelector('[data-calc="' + campo + '"]');
    if (siguiente) {
      var pos = state.calc[campo].length;
      siguiente.focus();
      siguiente.setSelectionRange(pos, pos);
    }
  });

  function cargar(nombre) {
    return fetch("data/open/" + nombre).then(function (resp) {
      if (!resp.ok) throw new Error(nombre);
      return resp.json();
    }).catch(function () { return null; });
  }

  Promise.all([
    cargar("conectividad.json"),
    cargar("wikipedia.json"),
    cargar("gdelt.json"),
    cargar("ema.json"),
    cargar("medata_tarifas.json"),
    cargar("icca.json"),
    cargar("evi.json"),
    cargar("huella.json"),
    cargar("manifiesto.json")
  ]).then(function (piezas) {
    DATA.conectividad = piezas[0];
    DATA.wikipedia = piezas[1];
    DATA.gdelt = piezas[2];
    DATA.ema = piezas[3];
    DATA.medata = piezas[4];
    DATA.icca = piezas[5];
    DATA.evi = piezas[6];
    DATA.huella = piezas[7];
    DATA.manifiesto = piezas[8];
    leerUrl();
    if (!DATA.conectividad || !DATA.ema || !DATA.icca) {
      document.getElementById("app").innerHTML = hueco("Faltan agregados", "Abra esta carpeta con un servidor local después de correr scripts/preparar_fuentes.py.");
      return;
    }
    render();
  });
}());
