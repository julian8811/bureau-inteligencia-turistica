import { chromium } from "playwright";
import { writeFile } from "node:fs/promises";

const base = "http://127.0.0.1:8765/";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const filas = [];

for (const tab of ["mercados", "visitante", "captacion", "miembros"]) {
  for (const anio of [2022, 2023, 2024, 2025, 2026]) {
    await page.goto(`${base}?tab=${tab}&anio=${anio}&pais=Todos`, { waitUntil: "networkidle" });
    await page.waitForSelector(".kpi, .stock, .hueco, .block");
    const bloques = await page.evaluate(() => {
      return [...document.querySelectorAll("#app .block")].map((b) => {
        const h3 = (b.querySelector("h3") || {}).textContent || "";
        const src = (b.querySelector(".src") || {}).textContent || "";
        return { titulo: h3.trim(), pie: src.trim() };
      });
    });
    const avisos = await page.evaluate(() => {
      return [...document.querySelectorAll("#app .aviso")].map((n) => n.textContent.trim());
    });
    filas.push({ tab, anio, nBloques: bloques.length, bloques, avisos });
  }
}
await browser.close();

// Declarado = pie fijo (corte/simulador/ejercicio/baseline) o vista con aviso de ola que cubre el fallback
const FIJO = [/corte 2025/i, /ICCA/i, /simulador/i, /ejercicio/i, /dic-2023/i, /ventana corriente/i, /sin corte/i, /sin mes/i, /enero – junio 2025/i, /agosto 2023/i];
const mezclados = [];
for (const f of filas) {
  const tieneAvisoOla = f.avisos.some((a) => /ola|microdato|última ola/i.test(a));
  for (const b of f.bloques) {
    if (!b.pie) { mezclados.push({ tab: f.tab, anio: f.anio, titulo: b.titulo, motivo: "sin pie" }); continue; }
    if (FIJO.some((re) => re.test(b.pie))) continue;
    if (/EVI/i.test(b.pie) && tieneAvisoOla) continue; // fallback EVI declarado en aviso de vista
    const m = b.pie.match(/20\d{2}/g) || [];
    if (m.length && !m.includes(String(f.anio))) {
      mezclados.push({ tab: f.tab, anio: f.anio, titulo: b.titulo, pie: b.pie, motivo: "año distinto al filtro" });
    }
  }
}
await writeFile("/tmp/tableros-bureau/qa/salida-anios.json", JSON.stringify({ filas, mezclados }, null, 2));
console.log(JSON.stringify({ vistas: filas.length, mezclados: mezclados.length, detalle: mezclados }, null, 2));
