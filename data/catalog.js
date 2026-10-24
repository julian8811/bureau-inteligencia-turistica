/* Catálogo de los 21 indicadores. La serie vive en data/open o en informe2025.js. */
window.CATALOGO = [
  {
    id: "conectividad", tab: "mercados", nombre: "Conectividad aérea con mercados priorizados",
    pastilla: "Dato abierto", clase: "abierto",
    fuenteTipo: "Secundaria", fuente: "Aerocivil, tráfico comercial origen-destino, datos.gov.co gb6w-ynu4",
    pedida: "Mensual", grano: "Mensual", unidad: "Pasajeros",
    formula: "Pasajeros comerciales del mes con un extremo en MDE o EOH y el otro en el mercado.",
    universo: "José María Córdova y Olaya Herrera. La lista de mercados está marcada para validar con el Bureau.",
    licencia: "Datos abiertos de la Aeronáutica Civil.",
    noMide: "Asientos ofrecidos ni frecuencias. La base publica pasajeros transportados."
  },
  {
    id: "busqueda", tab: "mercados", nombre: "Intención de búsqueda y share of voice digital",
    pastilla: "Proxy", clase: "proxy",
    fuenteTipo: "Secundaria", fuente: "Wikimedia Pageviews (CC0) y GDELT DOC 2.0",
    pedida: "Trimestral", grano: "Mensual, sumado al trimestre", unidad: "Índice y participación",
    formula: "Vistas o menciones de Medellín divididas por la suma del set de destinos.",
    universo: "Artículos de Wikipedia en español e inglés, y menciones del nombre de la ciudad en medios de GDELT.",
    licencia: "CC0 para Wikimedia. GDELT exige cita a https://www.gdeltproject.org/",
    noMide: "Búsquedas de Google. La API de Trends sigue en alfa cerrada y no se usa."
  },
  {
    id: "reservas", tab: "mercados", nombre: "Reservas hacia Medellín",
    pastilla: "Proxy", clase: "proxy",
    fuenteTipo: "Secundaria", fuente: "Aerocivil, llegadas a MDE y EOH",
    pedida: "Trimestral", grano: "Mensual, sumado al trimestre", unidad: "Pasajeros llegados",
    formula: "Pasajeros llegados a Medellín por mercado, sumados al trimestre.",
    universo: "Llegadas realizadas. El SIT publica reservas en su observatorio; esa cifra no está en un archivo descargable y no se copia.",
    licencia: "Datos abiertos de la Aeronáutica Civil.",
    noMide: "Reservas futuras de agencias ni de plataformas."
  },
  {
    id: "icca", tab: "mercados", nombre: "Participación ICCA y no ICCA",
    pastilla: "Cita anual", clase: "cita",
    fuenteTipo: "Secundaria", fuente: "ICCA GlobeWatch Country and City Rankings 2025, tabla de ciudades",
    pedida: "Trimestral", grano: "Anual", unidad: "Puesto y reuniones",
    formula: "Reuniones elegibles ICCA de la ciudad y su puesto en la tabla.",
    universo: "Asociaciones que rotan entre al menos tres países y reúnen 50 participantes o más, según la regla pública de ICCA.",
    licencia: "Cifras citadas del PDF difundido. La base Business Intelligence sigue siendo de miembros.",
    noMide: "Participación no ICCA, ferias UFI ni el corte trimestral."
  },
  {
    id: "tarifas", tab: "mercados", nombre: "Competitividad de tarifas de alojamiento",
    pastilla: "Dato abierto parcial", clase: "abierto",
    fuenteTipo: "Secundaria", fuente: "DANE, Encuesta Mensual de Alojamiento, índice de tarifa sencilla. Medata, tarifa por zona.",
    pedida: "Mensual", grano: "Mensual", unidad: "Índice, base regiones = 100",
    formula: "Índice de Antioquia dividido por el promedio de las regiones EMA de la fila, por 100.",
    universo: "Regiones de la EMA, acomodación sencilla, base DANE 2019=100. Antioquia no es la tarifa de la ciudad.",
    licencia: "Estadística oficial DANE. Medata: CC BY-SA 4.0, corte de publicación 14 de diciembre de 2023.",
    noMide: "La tarifa vigente de un hotel de Medellín ni la de Inside Airbnb, que no publica la ciudad."
  },
  {
    id: "conversion", tab: "mercados", nombre: "Tasa de conversión de mercados priorizados",
    pastilla: "Fuente primaria", clase: "primaria",
    fuenteTipo: "Primaria", fuente: "CRM de captación del Bureau",
    pedida: "Trimestral o semestral", grano: "Pendiente de extracto", unidad: "Tasa",
    formula: "Confirmados del mercado divididos por oportunidades de ese mercado.",
    universo: "Oportunidades del mercado priorizado en el CRM.",
    licencia: "Extracto del Bureau, cuando exista.",
    noMide: "El informe de gestión 2025 no parte la captación por mercado."
  },
  {
    id: "gasto", tab: "visitante", nombre: "Gasto promedio por visitante",
    pastilla: "Dato abierto", clase: "abierto",
    fuenteTipo: "Secundaria", fuente: "DANE, EVI, microdatos catálogo 869, ponderados con fexp",
    pedida: "Mensual", grano: "Ola publicada", unidad: "USD por persona",
    formula: "Gasto del grupo en dólares dividido por el tamaño del grupo. El diario divide ese valor por las noches del destino principal.",
    universo: "No residente encuestado en José María Córdova.",
    licencia: "Microdatos DANE. En el tablero solo hay promedios y la n ponderada.",
    noMide: "El visitante nacional ni un mes dentro de la ola."
  },
  {
    id: "grupo", tab: "visitante", nombre: "Grupo de viaje y estadía promedio",
    pastilla: "Dato abierto", clase: "abierto",
    fuenteTipo: "Secundaria", fuente: "DANE, EVI, catálogo 869",
    pedida: "Mensual", grano: "Ola publicada", unidad: "Personas y noches",
    formula: "Distribución ponderada del tamaño del grupo y media ponderada de Noches_per_prin.",
    universo: "No residente encuestado en José María Córdova.",
    licencia: "Microdatos DANE, solo agregados.",
    noMide: "La estadía en la ciudad cuando el destino principal del viaje es otro departamento."
  },
  {
    id: "nps", tab: "visitante", nombre: "Satisfacción y NPS del destino",
    pastilla: "Fuente primaria", clase: "primaria",
    fuenteTipo: "Secundaria y/o primaria", fuente: "Encuesta de destino del Bureau o del SIT, cuando exista microdato",
    pedida: "Mensual", grano: "Pendiente de extracto", unidad: "NPS y escala",
    formula: "Porcentaje de promotores menos porcentaje de detractores. La satisfacción va en una escala aparte.",
    universo: "Visitantes del destino que responden la encuesta.",
    licencia: "Pendiente.",
    noMide: "La EVI publicada no trae promotores ni detractores. No se mezcla con la calificación de miembros."
  },
  {
    id: "perfil", tab: "visitante", nombre: "Perfil demográfico y motivaciones",
    pastilla: "Dato abierto", clase: "abierto",
    fuenteTipo: "Secundaria", fuente: "DANE, EVI, catálogo 869",
    pedida: "Trimestral", grano: "Ola publicada", unidad: "Participación",
    formula: "Peso ponderado de la residencia y del motivo principal del viaje.",
    universo: "No residente encuestado en José María Córdova. La ola se muestra completa.",
    licencia: "Microdatos DANE, solo agregados.",
    noMide: "Edad: esa variable no está en la base aéreo-marítimo usada."
  },
  {
    id: "huella", tab: "visitante", nombre: "Huella de carbono promedio",
    pastilla: "Proxy", clase: "proxy",
    fuenteTipo: "Secundaria", fuente: "EVI, OurAirports y factores de conversión del Reino Unido 2026",
    pedida: "Anual", grano: "Ola de la EVI", unidad: "kg CO2e por persona",
    formula: "Distancia de ida del país de residencia a MDE por el factor aéreo, más noches medias por el factor de hotel.",
    universo: "No residente de la EVI con país mapeado a un aeropuerto de referencia.",
    licencia: "Factores oficiales para reporte de GEI. El uso fuera de ese reporte queda bajo responsabilidad de quien los aplica.",
    noMide: "Una medición directa ni el tramo de regreso. El factor de hotel se aplica por noche de persona."
  },
  {
    id: "scoring", tab: "captacion", nombre: "Prioridad de mercado para captación",
    pastilla: "Prioridad de mercado", clase: "derivada",
    fuenteTipo: "Primaria en el encargo; el ejercicio usa señales abiertas",
    fuente: "Aerocivil y EVI. El informe 2025 no trae puntajes de organizadores.",
    pedida: "Mensual o por evento", grano: "Año del filtro, con la ola EVI que lo cubre", unidad: "Índice 0 a 100",
    formula: "40 % pasajeros del mercado, 30 % llegadas y 30 % gasto de estadía EVI, cada uno llevado a 0–100 según el máximo del set.",
    universo: "Mercados priorizados. Pageviews y menciones describen al destino y no se parten por país de origen, por eso no entran al índice.",
    licencia: "Lectura derivada de las fuentes abiertas. No es el lead scoring del CRM.",
    noMide: "El puntaje de un organizador ni el nombre de una asociación."
  },
  {
    id: "inspeccion", tab: "captacion", nombre: "Efectividad de visitas de inspección",
    pastilla: "Fuente primaria", clase: "primaria",
    fuenteTipo: "Primaria", fuente: "Registro de inspecciones del Bureau",
    pedida: "Mensual o por evento", grano: "Pendiente de extracto", unidad: "Tasa",
    formula: "Candidaturas confirmadas después de la inspección divididas por inspecciones realizadas.",
    universo: "Visitas de inspección de sede. Los fam trips vacacionales de 2025 no se usan aquí.",
    licencia: "Pendiente.",
    noMide: "Una serie publicada. La calculadora de esta pantalla no se guarda."
  },
  {
    id: "roi", tab: "captacion", nombre: "Aporte estimado de los eventos captados",
    pastilla: "Lectura derivada", clase: "derivada",
    fuenteTipo: "Primaria", fuente: "Informe de gestión 2025 del Bureau",
    pedida: "Anual o por evento", grano: "Anual 2025", unidad: "USD",
    formula: "Impacto estimado dividido por eventos captados, y dividido por asistentes proyectados. El ROI sería beneficio dividido por costo de captación.",
    universo: "103 eventos captados y apoyados en 2025, con su impacto, asistentes y cuartos noche publicados.",
    licencia: "Cifra citada del informe de gestión.",
    noMide: "El costo de captación ni el impacto por segmento. Los dólares no se reparten entre los 59 internacionales y los 44 nacionales."
  },
  {
    id: "flujo", tab: "captacion", nombre: "Flujo de captación",
    pastilla: "Cita informe 2025", clase: "cita",
    fuenteTipo: "Primaria", fuente: "Informe de gestión 2025 del Bureau",
    pedida: "Por evento", grano: "Anual 2025", unidad: "Eventos",
    formula: "Tres stocks con universos distintos: investigados, candidaturas presentadas, eventos captados y apoyados.",
    universo: "El informe no presenta estas tres cifras como embudo de la misma cohorte.",
    licencia: "Cifra citada.",
    noMide: "Una tasa entre los tres stocks. Los captados no son un subconjunto de las candidaturas."
  },
  {
    id: "perdidas", tab: "captacion", nombre: "Motivos de pérdida de candidatura",
    pastilla: "Fuente primaria", clase: "primaria",
    fuenteTipo: "Primaria", fuente: "CRM de candidaturas del Bureau",
    pedida: "Semestral o por evento", grano: "Pendiente de extracto", unidad: "Participación",
    formula: "Candidaturas no confirmadas por motivo, sobre el total de candidaturas no confirmadas.",
    universo: "Candidaturas perdidas.",
    licencia: "Pendiente.",
    noMide: "El tono de la prensa ni una hipótesis de motivos."
  },
  {
    id: "valor", tab: "miembros", nombre: "Valor de vida del miembro",
    pastilla: "Fuente primaria", clase: "primaria",
    fuenteTipo: "Primaria", fuente: "Libro de miembros del Bureau",
    pedida: "Anual", grano: "Pendiente de extracto", unidad: "Pesos por miembro",
    formula: "Cuota por años de permanencia esperados, más el margen de beneficios consumidos.",
    universo: "Cohorte de miembros.",
    licencia: "Pendiente. La cuota y la permanencia no están en el informe.",
    noMide: "La expectativa de la rueda, que es un flujo de un año y se muestra en otra tarjeta."
  },
  {
    id: "engagement", tab: "miembros", nombre: "Participación en la Rueda de Negocios",
    pastilla: "Lectura derivada", clase: "derivada",
    fuenteTipo: "Primaria", fuente: "Informe de gestión 2025 del Bureau",
    pedida: "Trimestral", grano: "Anual 2025", unidad: "Tasa",
    formula: "Miembros participantes en la rueda divididos por el padrón de cierre. Efectividad: citas que cumplieron expectativas divididas por citas gestionadas.",
    universo: "Una actividad, la Rueda de Negocios 2025. No es un índice de todos los beneficios.",
    licencia: "Cifra citada y división de cifras del mismo universo.",
    noMide: "Asistencia a otras actividades, uso de beneficios ni las redes del Bureau."
  },
  {
    id: "retencion", tab: "miembros", nombre: "Retención y deserción",
    pastilla: "Fuente primaria", clase: "primaria",
    fuenteTipo: "Primaria", fuente: "Libro de miembros del Bureau",
    pedida: "Anual", grano: "Pendiente el padrón de apertura", unidad: "Tasa",
    formula: "Deserción = bajas divididas por el padrón de inicio de año. Retención = 1 − deserción.",
    universo: "Padrón de miembros. El informe publica el cierre (200) y las altas (23).",
    licencia: "El 23/200 es la participación de las altas en el cierre, no la deserción.",
    noMide: "La tasa de deserción, porque falta el padrón con el que abrió 2025."
  },
  {
    id: "oportunidades", tab: "miembros", nombre: "Oportunidades comerciales de la Rueda",
    pastilla: "Cita informe 2025", clase: "cita",
    fuenteTipo: "Primaria", fuente: "Informe de gestión 2025 del Bureau",
    pedida: "Semestral", grano: "Anual 2025", unidad: "Citas y pesos",
    formula: "Expectativa de negocio dividida por citas y por miembros participantes.",
    universo: "Rueda de Negocios 2025. Es expectativa, no venta cerrada ni lead entregado.",
    licencia: "Cifra citada.",
    noMide: "Oportunidades canalizadas fuera de la rueda ni el cierre de la venta."
  },
  {
    id: "satisfaccion", tab: "miembros", nombre: "Confianza y satisfacción del miembro",
    pastilla: "Cita informe 2025", clase: "cita",
    fuenteTipo: "Primaria", fuente: "Informe de gestión 2025 del Bureau",
    pedida: "Semestral", grano: "Anual 2025", unidad: "Escala de 1 a 5",
    formula: "Calificación de la gestión del Bureau por los miembros.",
    universo: "Miembros que respondieron. La n no aparece en el informe.",
    licencia: "Cifra citada.",
    noMide: "Una segunda escala de confianza ni un NPS. El texto menciona la confianza y no le asigna número."
  }
];

window.fichaPorId = function (id) {
  return window.CATALOGO.find(function (item) { return item.id === id; });
};
