# Modelo Power BI — Turismo 2025-2026 (Colmayor)

Carpeta: `/home/julian/Bureau/powerbi-turismo/` · 16 CSV + tema + DAX

## 1. Modelo estrella (17 tablas · 19 relaciones · 25 medidas)
Hechos `01`–`08` (cada uno con FK oculta `id_fuente` → `09_dim_fuente`): llegadas, regiones 2025, regiones H1, gasto, Eurostat, aéreo, hotel, Colombia. Dimensiones: `dim_anio` (2019–2026), `09_dim_fuente` (16 fuentes), `10_dim_region`, `11_dim_periodo` (tipo Anual/Trimestre/Semestre), `12_dim_indicador_gasto`, `13_dim_origen`, `14_dim_indicador_aereo`, `15_dim_mercado`, `16_dim_segmento`. Todas 1:N de un solo sentido, sin relaciones hecho–hecho (verificadas 0 huérfanos).

1. Power BI Desktop > abrir el `.PBIT` > **Actualizar** (datos inline, UTF-8 con BOM).
2. El tema Colmayor va embebido; paleta #172139/#108181/#00AEAC/#E9901E/#B4C42C.
3. Medidas: ya vienen en el modelo (`DAX_medidas.dax` las documenta una por una).

## 2. Páginas del informe (6)
| Página | Visuales | Tablas |
|---|---|---|
| 1 Portada KPI | 4 tarjetas: 1.520 M 2025 · 690 M H1 · USD 1,9 T · USD 12 T WTTC + tabla `09_dim_fuente` | 01, 04, 09 |
| 2 Llegadas global | Barras por periodo (llegadas M) + tarjeta H1 + segmentador periodo | 01 |
| 3 Regiones | Barras 2025 por región (M) + barras H1 2026 (crec. %) | 02, 03 |
| 4 Gasto | 2 tarjetas (Receipts, WTTC) + tabla detalle gasto | 04 |
| 5 Europa + Aéreo + Hotel | Barras Eurostat noches + tabla IATA + tabla hotel STR | 05, 06, 07 |
| 6 Colombia + Fuentes | 2 tarjetas (visitantes, share joven) + tabla Colombia + tabla `09_dim_fuente` | 08, 09 |

> Sin mapa coroplético por decisión: las regiones agregadas (Europa, Asia-Pacífico...) no son países y el mapa no las geocodifica; las barras son la comparativa correcta. Los periodos se solapan (H1 = Q1+Q2): comparar barras, no sumarlas.

## 3. Detalle por visual (qué campo va dónde)
- **Barras llegadas:** Eje = `periodo`, Valores = `Llegadas M`, Etiquetas activadas, color base #172139, destacado 2025 #00AEAC.
- **Regiones 2025:** Eje = `region`, Valores = `llegadas_M_2025`, tooltip `var_vs_2024_pct` y `var_vs_2019_pct`.
- **H1 2026 %:** Eje = `region`, Valores = `crec_H1_2026_pct`, colores condicionales: <0 → #C0392B, ≥0 → #108181.
- **Colombia edad:** Eje = `categoria`, Valores = `valor` (filtrar segmento=Edad), + tarjeta `Share Joven CO %`.
- **Tabla fuentes:** columnas id/base/edición/acceso/fecha_pub/url_corta de `09_dim_fuente`.

## 4. Filtros y segmentaciones
- Segmentador `anio` (01) y `periodo` para alternar anual/H1/Q.
- Segmentador `origen` (05: Internacional/Doméstico) en página Europa.
- Filtro de página `fuente` para auditoría (cada cifra trae su fuente).

## 5. Validaciones (QA antes de publicar)
- [ ] Suma regiones 2025 ≈ 1.523 M (≈ 1.520 M global, dif. redondeo OK).
- [ ] H1 2026 = 690 M; Q1 307 + Q2 383 = 690 ✓.
- [ ] Eurostat H1 intl + dom = total (645,4 + 675,7 = 1.321 ≈ 1.300 por redondeo/unidades — documentar).
- [ ] Formato: M con 0-1 decimal, USD T con 2, % con 1.

## 6. Publicar
- Guardar como `turismo-2025-2026-Colmayor.pbix` junto a esta carpeta (los CSV quedan como fuente).
- Si se automatiza: **Transformar datos > Origen** apuntar a esta carpeta; actualizar = reemplazar CSV y Actualizar.

Archivos: 01–08 hechos (+`id_fuente`), 09 catálogo (16 fuentes), 10–16 dims, `dim_anio` sintética, tema JSON válido (esquema oficial), DAX (25 medidas). Todo UTF-8-SIG para tildes.

## 7. Plantilla .PBIT incluida (nuevo)
- `turismo-2025-2026-Colmayor.pbit`: 17 tablas + 25 medidas + 19 relaciones + 6 páginas con 34 visuales reales (tarjetas, barras, tablas, segmentador). Generado con `build_pbix.py` + `pbi-tools` (script reproducible; ver `pbixproj-turismo/`).
- **Uso:** doble clic en Windows con Power BI Desktop > **Actualizar** (los datos van inline en el propio archivo, no pide credenciales) > **Guardar como .PBIX**. El tema Colmayor va embebido en el propio informe (ya no hace falta importarlo a mano).
- Nota técnica: `pbi-tools` solo compila PBIX para reportes "thin"; con modelo de datos el formato correcto es PBIT (la vía oficial plantilla → PBIX). Recompilar: `python3 build_pbix.py`.
