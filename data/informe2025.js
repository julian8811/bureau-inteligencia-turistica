/* Cifras citadas del informe de gestión 2025.
   Fuente: https://bureaumedellin.com/wp-content/uploads/2026/02/INFORME-2_Entrega3.pdf
   Las divisiones se hacen en app.js solo cuando el numerador y el denominador comparten universo. */
window.INFORME = {
  fuente: "Informe de gestión 2025, Greater Medellín Convention & Visitors Bureau",
  url: "https://bureaumedellin.com/wp-content/uploads/2026/02/INFORME-2_Entrega3.pdf",
  anio: 2025,
  flujo: [
    {
      etiqueta: "Eventos investigados",
      valor: "más de 370",
      universo: "Eventos potenciales investigados durante 2025."
    },
    {
      etiqueta: "Candidaturas presentadas",
      valor: "30",
      universo: "Candidaturas presentadas. No es un subconjunto declarado de los 370."
    },
    {
      etiqueta: "Eventos captados y apoyados",
      valor: "103",
      detalle: "59 internacionales y 44 nacionales",
      universo: "Eventos captados y apoyados. Supera a las 30 candidaturas, así que no es su confirmación."
    }
  ],
  captados: 103,
  internacionales: 59,
  nacionales: 44,
  impactoUsd: 156168654,
  asistentes: 242019,
  cuartosNoche: 752214,
  realizados: { eventos: 111, asistentes: 266875, derramaMillonesUsd: 167 },
  miembros: 200,
  altas: 23,
  segmentosAltas: ["Agencias de viaje receptivo", "Alojamientos", "Operadores de eventos", "Recintos", "Proveedores de servicios"],
  rueda: { miembros: 68, citas: 433, cumplieron: 418, expectativa: 7925390000, efectividadInforme: 0.965 },
  satisfaccion: 4.9,
  satisfaccionEscala: 5
};
