/* Gráficos SVG con la paleta del Manual V7. El morado y la trama son solo simulación. */
window.Charts = (function () {
  var palette = ["#E9901E", "#108181", "#FBBB28", "#195855", "#00AEAC", "#172139", "#B4C42C"];
  var SIM = "#6E5A8A";
  var foco = "";
  var serieSvg = 0;

  function esc(text) {
    return String(text == null ? "" : text).replace(/[&<>"]/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
    });
  }

  function eje(n) {
    var abs = Math.abs(n);
    if (abs >= 1000000) return (n / 1000000).toFixed(1).replace(".", ",") + " M";
    if (abs >= 1000) return Math.round(n / 1000) + " mil";
    if (abs >= 10) return String(Math.round(n));
    return (Math.round(n * 10) / 10).toString().replace(".", ",");
  }

  function trama() {
    serieSvg += 1;
    var id = "trama" + serieSvg;
    var def = '<defs><pattern id="' + id + '" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(32)">' +
      '<rect width="6" height="6" fill="#f4f0f8"></rect>' +
      '<line x1="0" y1="0" x2="0" y2="6" stroke="' + SIM + '" stroke-width="2"></line></pattern></defs>';
    return { id: id, def: def };
  }

  function tinta(item, fallback, id) {
    if (item && item.sim) return "url(#" + id + ")";
    return (item && item.color) || fallback || palette[0];
  }

  function marca(item, tip) {
    var texto = tip || item.tip || "";
    if (!texto && item.label != null && item.value != null) texto = item.label + ": " + (item.text || eje(item.value));
    var html = "";
    if (texto) html += ' data-tip="' + esc(texto) + '"';
    if (item && item.pais) html += ' data-pais="' + esc(item.pais) + '"';
    if (item && item.pais && item.pais === foco) html += ' class="foco"';
    return html;
  }

  function leyenda(items) {
    if (!items || !items.length) return "";
    return '<div class="leyenda">' + items.map(function (item, i) {
      var fondo = item.sim ? SIM : item.color;
      return '<span><i class="' + (item.sim ? "sim" : "") + " trazo-" + (item.trazo == null ? i : item.trazo) + '" style="background:' + fondo + '"></i>' + esc(item.name) + "</span>";
    }).join("") + "</div>";
  }

  function figura(svg, items, sim) {
    return '<div class="figura marco' + (sim ? " simulado" : "") + '" tabindex="0">' + svg + leyenda(items) + "</div>";
  }

  function enmarcar(svg, sim) {
    return '<div class="marco' + (sim ? " simulado" : "") + '" tabindex="0">' + svg + "</div>";
  }

  function grilla(width, height, padL, padB, max) {
    var top = 16;
    var plotH = height - padB - top;
    var marcas = [0, 0.5, 1];
    return marcas.map(function (t) {
      var y = top + plotH - t * plotH;
      return '<line x1="' + padL + '" y1="' + y + '" x2="' + (width - 12) + '" y2="' + y + '" stroke="#e4ecec" stroke-width="1"></line>' +
        '<text x="' + (padL - 6) + '" y="' + (y + 3) + '" font-size="10" fill="#6b7789" text-anchor="end">' + esc(eje(max * t)) + "</text>";
    }).join("");
  }

  function yDe(value, max, height, padB) {
    var top = 16;
    var plotH = height - padB - top;
    return top + plotH - (value / max) * plotH;
  }

  function line(series, color, options) {
    options = options || {};
    var width = 640, height = 220, padL = 52, padB = 28;
    var patron = trama();
    if (!series.length) return "";
    var max = Math.max.apply(null, series.map(function (p) { return p.y; }).concat([options.mark || 0, 1]));
    var step = series.length === 1 ? 0 : (width - padL - 16) / (series.length - 1);
    var pts = series.map(function (p, i) {
      return (padL + i * step) + "," + yDe(p.y, max, height, padB);
    }).join(" ");
    var area = padL + "," + yDe(0, max, height, padB) + " " + pts + " " + (padL + (series.length - 1) * step) + "," + yDe(0, max, height, padB);
    var salto = Math.ceil(series.length / 6);
    var axis = series.filter(function (_, i) { return i % salto === 0; }).map(function (p) {
      var i = series.indexOf(p);
      return '<text x="' + (padL + i * step) + '" y="' + (height - 8) + '" font-size="10" fill="#6b7789" text-anchor="middle">' + esc(p.x) + "</text>";
    }).join("");
    var puntos = series.map(function (p, i) {
      var x = padL + i * step;
      var y = yDe(p.y, max, height, padB);
      return '<circle cx="' + x + '" cy="' + y + '" r="4" fill="' + color + '"' + marca({ tip: (p.tip || p.x) + ": " + eje(p.y), pais: p.pais }) + "></circle>";
    }).join("");
    var marcaY = "";
    if (options.mark != null) {
      var y = yDe(options.mark, max, height, padB);
      marcaY = '<line x1="' + padL + '" y1="' + y + '" x2="' + (width - 12) + '" y2="' + y + '" stroke="#B4C42C" stroke-dasharray="4 3" stroke-width="1.5"></line>';
    }
    var svg = '<svg class="chart" viewBox="0 0 ' + width + " " + height + '" role="img">' + patron.def +
      grilla(width, height, padL, padB, max) + marcaY +
      '<polygon points="' + area + '" fill="' + color + '" opacity="0.12"></polygon>' +
      '<polyline fill="none" stroke="' + color + '" stroke-width="2.5" points="' + pts + '"></polyline>' + puntos + axis + "</svg>";
    return options.mark != null ? figura(svg, [{ name: "Referencia " + options.mark, color: "#B4C42C" }]) : enmarcar(svg);
  }

  function multiLine(series) {
    var width = 640, height = 240, padL = 52, padB = 28;
    var patron = trama();
    var labels = [];
    var max = 1;
    series.forEach(function (s) {
      s.points.forEach(function (p) {
        if (labels.indexOf(p.x) < 0) labels.push(p.x);
        if (p.y > max) max = p.y;
      });
    });
    if (!labels.length) return "";
    var step = labels.length === 1 ? 0 : (width - padL - 16) / (labels.length - 1);
    var salto = Math.ceil(labels.length / 6);
    var axis = labels.filter(function (_, i) { return i % salto === 0; }).map(function (label) {
      var i = labels.indexOf(label);
      return '<text x="' + (padL + i * step) + '" y="' + (height - 8) + '" font-size="10" fill="#6b7789" text-anchor="middle">' + esc(label) + "</text>";
    }).join("");
    var trazos = ["0", "7 4", "2 3", "9 3 2 3", "4 2"];
    var lineas = series.map(function (s, serie) {
      var pts = s.points.map(function (p) {
        var i = labels.indexOf(p.x);
        return (padL + i * step) + "," + yDe(p.y, max, height, padB);
      }).join(" ");
      var circulos = s.points.map(function (p) {
        var i = labels.indexOf(p.x);
        var x = padL + i * step;
        var y = yDe(p.y, max, height, padB);
        return '<circle cx="' + x + '" cy="' + y + '" r="4" fill="' + s.color + '"' + marca({ tip: s.name + " · " + p.x + ": " + eje(p.y), pais: s.pais }) + "></circle>";
      }).join("");
      return '<polyline fill="none" stroke="' + s.color + '" stroke-width="2.4" stroke-dasharray="' + trazos[serie % trazos.length] + '" points="' + pts + '"></polyline>' + circulos;
    }).join("");
    var svg = '<svg class="chart" viewBox="0 0 ' + width + " " + height + '" role="img">' + patron.def +
      grilla(width, height, padL, padB, max) + lineas + axis + "</svg>";
    return figura(svg, series.map(function (s, i) { return { name: s.name, color: s.color, trazo: i }; }));
  }

  function bars(items, color) {
    var width = 640, row = 28, labelW = 196;
    var height = Math.max(40, items.length * row + 8);
    var patron = trama();
    var max = Math.max.apply(null, items.map(function (p) { return p.value; }).concat([1]));
    var sim = items.some(function (item) { return item.sim; });
    var body = items.map(function (item, i) {
      var y = 6 + i * row;
      var textoValor = String(item.text || eje(item.value));
      var reserva = Math.min(150, 6.6 * textoValor.length + 10);
      var hueco = Math.max(24, width - labelW - reserva - 8);
      var w = Math.max(2, (item.value / max) * hueco);
      var relleno = tinta(item, item.color || color || palette[i % palette.length], patron.id);
      var etiqueta = item.label || "";
      var visible = etiqueta.length > 26 ? etiqueta.slice(0, 25) + "…" : etiqueta;
      return '<text x="0" y="' + (y + 14) + '" font-size="11" fill="#172139">' + esc(visible) + "</text>" +
        '<rect x="' + labelW + '" y="' + y + '" width="' + w + '" height="16" rx="3" fill="' + relleno + '"' + marca(item) + "></rect>" +
        '<text x="' + (labelW + 6 + w) + '" y="' + (y + 13) + '" font-size="11" fill="#3d4a5c">' + esc(textoValor) + "</text>";
    }).join("");
    return enmarcar('<svg class="chart" viewBox="0 0 ' + width + " " + height + '" role="img">' + patron.def + body + "</svg>", sim && items.every(function (item) { return item.sim; }));
  }

  function columns(items) {
    var width = 640, height = 220, padL = 52, padB = 28;
    var patron = trama();
    var max = Math.max.apply(null, items.map(function (p) { return p.value; }).concat([1]));
    var gap = 10;
    var col = items.length ? (width - padL - 16 - gap * (items.length - 1)) / items.length : 0;
    var base = yDe(0, max, height, padB);
    var sim = items.length && items.every(function (item) { return item.sim; });
    var body = items.map(function (item, i) {
      var y = yDe(item.value, max, height, padB);
      var x = padL + i * (col + gap);
      return '<rect x="' + x + '" y="' + y + '" width="' + col + '" height="' + Math.max(0, base - y) + '" rx="3" fill="' + tinta(item, palette[i % palette.length], patron.id) + '"' + marca(item) + "></rect>" +
        '<text x="' + (x + col / 2) + '" y="' + (height - 8) + '" font-size="10" fill="#6b7789" text-anchor="middle">' + esc(item.label) + "</text>";
    }).join("");
    return enmarcar('<svg class="chart" viewBox="0 0 ' + width + " " + height + '" role="img">' + patron.def + grilla(width, height, padL, padB, max) + body + "</svg>", sim);
  }

  function stacked(items) {
    var width = 640, height = 240, padL = 52, padB = 28;
    var patron = trama();
    var nombres = [];
    items.forEach(function (item) {
      (item.parts || []).forEach(function (part) {
        if (!nombres.some(function (n) { return n.name === part.name; })) nombres.push({ name: part.name, color: part.color, sim: part.sim });
      });
    });
    var max = 1;
    items.forEach(function (item) {
      var suma = (item.parts || []).reduce(function (s, p) { return s + p.value; }, 0);
      if (suma > max) max = suma;
    });
    var gap = 8;
    var col = items.length ? (width - padL - 16 - gap * (items.length - 1)) / items.length : 0;
    var base = yDe(0, max, height, padB);
    var body = items.map(function (item, i) {
      var x = padL + i * (col + gap);
      var cursor = 0;
      var rects = (item.parts || []).map(function (part) {
        var y0 = yDe(cursor, max, height, padB);
        cursor += part.value;
        var y1 = yDe(cursor, max, height, padB);
        var pieza = { label: item.label + " · " + part.name, value: part.value, pais: part.pais || item.pais, sim: part.sim, tip: item.label + " · " + part.name + ": " + eje(part.value) };
        return '<rect x="' + x + '" y="' + y1 + '" width="' + col + '" height="' + Math.max(0, y0 - y1) + '" fill="' + tinta(part, part.color, patron.id) + '"' + marca(pieza) + "></rect>";
      }).join("");
      return rects + '<text x="' + (x + col / 2) + '" y="' + (height - 8) + '" font-size="10" fill="#6b7789" text-anchor="middle">' + esc(item.label) + "</text>";
    }).join("");
    return figura('<svg class="chart" viewBox="0 0 ' + width + " " + height + '" role="img">' + patron.def + grilla(width, height, padL, padB, max) + body + "</svg>", nombres);
  }

  function grouped(groups) {
    var width = 640, height = 240, padL = 52, padB = 36;
    var patron = trama();
    var nombres = [];
    var max = 1;
    groups.forEach(function (group) {
      (group.bars || []).forEach(function (bar) {
        if (bar.value > max) max = bar.value;
        if (!nombres.some(function (n) { return n.name === bar.name; })) nombres.push({ name: bar.name, color: bar.color, sim: bar.sim });
      });
    });
    var n = groups.length || 1;
    var gap = 16;
    var slot = (width - padL - 16 - gap * (n - 1)) / n;
    var base = yDe(0, max, height, padB);
    var body = groups.map(function (group, i) {
      var bars = group.bars || [];
      var inner = 3;
      var w = Math.max(4, (slot - inner * (bars.length - 1)) / (bars.length || 1));
      var x0 = padL + i * (slot + gap);
      var rects = bars.map(function (bar, j) {
        var y = yDe(bar.value, max, height, padB);
        var x = x0 + j * (w + inner);
        var pieza = { label: group.label + " · " + bar.name, value: bar.value, pais: bar.pais || group.pais, sim: bar.sim, text: bar.text, tip: group.label + " · " + bar.name + ": " + (bar.text || eje(bar.value)) };
        return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + Math.max(0, base - y) + '" rx="2" fill="' + tinta(bar, bar.color, patron.id) + '"' + marca(pieza) + "></rect>";
      }).join("");
      return rects + '<text x="' + (x0 + slot / 2) + '" y="' + (height - 14) + '" font-size="10" fill="#6b7789" text-anchor="middle">' + esc(group.label) + "</text>";
    }).join("");
    return figura('<svg class="chart" viewBox="0 0 ' + width + " " + height + '" role="img">' + patron.def + grilla(width, height, padL, padB, max) + body + "</svg>", nombres);
  }

  function donut(items) {
    var patron = trama();
    var total = items.reduce(function (s, item) { return s + item.value; }, 0) || 1;
    var r = 58, c = 2 * Math.PI * r, offset = 0;
    var sim = items.length && items.every(function (item) { return item.sim; });
    var arcos = items.map(function (item) {
      var len = item.value / total * c;
      var nodo = '<circle cx="80" cy="80" r="' + r + '" fill="none" stroke="' + (item.sim ? SIM : item.color) + '" stroke-width="22" stroke-dasharray="' + len + " " + (c - len) + '" stroke-dashoffset="' + (-offset) + '" transform="rotate(-90 80 80)"' + marca(item) + "></circle>";
      offset += len;
      return nodo;
    }).join("");
    var svg = '<svg class="chart donut" viewBox="0 0 160 160" role="img">' + patron.def + arcos + "</svg>";
    return figura(svg, items.map(function (item) {
      return { name: item.label + " · " + (item.text || eje(item.value)), color: item.sim ? SIM : item.color, sim: item.sim };
    }), sim);
  }

  return {
    line: line,
    multiLine: multiLine,
    bars: bars,
    columns: columns,
    stacked: stacked,
    grouped: grouped,
    donut: donut,
    palette: palette,
    SIM: SIM,
    setFoco: function (valor) { foco = valor || ""; }
  };
}());
