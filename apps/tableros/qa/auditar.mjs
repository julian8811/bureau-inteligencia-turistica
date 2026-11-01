import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const raiz = path.dirname(fileURLToPath(import.meta.url));
const salida = path.join(raiz, "salida");
await mkdir(salida, { recursive: true });

const base = "http://127.0.0.1:8765/";
const browser = await chromium.launch();
const hallazgos = [];

async function medir(page) {
  return page.evaluate(() => {
    const textos = [];
    document.querySelectorAll("svg.chart text").forEach((node) => {
      const svg = node.ownerSVGElement;
      const vb = svg.viewBox.baseVal;
      if (!vb || !vb.width) return;
      const box = node.getBBox();
      const fuera = box.x < -2 || box.y < -2 || box.x + box.width > vb.width + 2 || box.y + box.height > vb.height + 2;
      if (fuera) textos.push(node.textContent.trim() + " @" + Math.round(box.x) + "+" + Math.round(box.width) + "/" + Math.round(vb.width));
    });
    const grillas = [...document.querySelectorAll(".g3")].map((grilla, i) => {
      const hijos = [...grilla.children];
      const alturas = hijos.map((hijo) => Math.round(hijo.getBoundingClientRect().height));
      const max = Math.max.apply(null, alturas.concat([0]));
      const min = Math.min.apply(null, alturas.concat([max]));
      return { i, n: hijos.length, alturas, desnivel: max - min, incompleta: hijos.length % 3 !== 0 };
    });
    const cuerpo = document.body.innerText;
    return {
      desborde: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      textos,
      grillas,
      orden: [...document.querySelectorAll("#app .block h3")].map((nodo) => nodo.textContent.trim()),
      tasas: /103\/30|30\/370/.test(cuerpo),
      simulaciones: (cuerpo.match(/Supuesto:/g) || []).length
    };
  });
}

for (const ancho of [1280, 390]) {
  const page = await browser.newPage({ viewport: { width: ancho, height: 900 } });
  for (const tab of ["mercados", "visitante", "captacion", "miembros"]) {
    await page.goto(base + "?tab=" + tab + "&anio=2025&pais=Todos", { waitUntil: "networkidle" });
    await page.waitForSelector(".kpi, .stock, .hueco");
    const medida = await medir(page);
    hallazgos.push({ ancho, tab, ...medida });
    await page.screenshot({ path: path.join(salida, ancho + "-" + tab + ".png"), fullPage: true });
  }
  await page.close();
}

const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.goto(base + "?tab=mercados&anio=2025&pais=PANAMA", { waitUntil: "networkidle" });
const panama = await page.locator(".kpi .value").first().innerText();
const punto = page.locator("[data-tip]").first();
await punto.hover();
const tip = await page.locator("#tip").innerText();
await punto.click();
const pais = new URL(page.url()).searchParams.get("pais");
hallazgos.push({ prueba: "panama", valor: panama, tip, paisTrasClic: pais });
await browser.close();

await writeFile(path.join(salida, "informe.json"), JSON.stringify(hallazgos, null, 2));
const graves = hallazgos.filter((item) => item.desborde > 2 || (item.textos && item.textos.length) || (item.grillas || []).some((g) => g.incompleta || g.desnivel > 280));
console.log(JSON.stringify({ panes: hallazgos.length, graves: graves.map((item) => ({
  ancho: item.ancho,
  tab: item.tab,
  desborde: item.desborde,
  textos: (item.textos || []).length,
  grillas: item.grillas,
  orden: item.orden
})) }, null, 2));
