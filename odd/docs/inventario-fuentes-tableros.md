# Inventario de fuentes del tablero y propuesta de fuentes nuevas

Revisión del 2 de noviembre de 2026 (hora Colombia) sobre:

- Tablero publicado: https://tableros-bureau.vercel.app/ (repo `julian8811/tableros-bureau`, `data/open/*.json`).
- ETL: este repo (`etl-bureau/`), corrida diaria en `.github/workflows/daily.yml`.
- Matriz original de bases: `matriz_bases_datos_bureau_medellin.xlsx` (31 bases + Plan Dashboard).

Convenciones de estado:

| Estado | Significado |
|---|---|
| Diaria | Se regenera en cada corrida del daily y llega al tablero vía `publicar.py` + `alimentar_bureau.py`. |
| Foto manual | El JSON del tablero se generó una vez a mano; nada en el daily lo vuelve a producir. |
| Cita | Cifra copiada de un informe o PDF; se actualiza cuando sale la nueva edición. |
| Pendiente | La pestaña tiene el indicador pero no hay extracto (dato primario del Bureau). |
| Roto | La fuente está cableada pero hoy devuelve error o 0 filas. |

---

## 1. Hallazgos críticos (arreglar antes de sumar fuentes)

1. **El daily está caído desde la corrida del 2-nov.** `orchestration/daily.py` importa 10 módulos que no están en el repo, y la corrida falla en la línea de import antes de extraer nada:
   `dane_ema`, `socrata_operaciones`, `socrata_migrantes`, `opensky_mde`, `aerodatabox_mde`, `ticketmaster_eventos`, `opentripmap_med`, `gated_amadeus`, `gated_brand24`, `gated_flightpowers`.
   El commit `7b83d61` (tanda-1) cableó estos módulos sin subir los archivos. `gated_amadeus` y `gated_brand24` se borraron a propósito el 28-oct (`odd/tasks/fuentes-rotar-skip.md`), pero el daily todavía los importa. Hay que subir los que existan en la máquina local o quitar los imports. Hasta entonces, ninguna pieza "Diaria" se actualiza.
2. **7 de las 10 piezas del ETL que muestra el tablero son fotos manuales.** Los exportadores `export/bureau_{oferta,seguridad,clima,conectividad,calendario,owid,sit}.py` no están en el daily, y `export/publicar.py` (`PIEZAS`) solo publica `paises`, `marca_llm`, `prensa_medios`, `informe_llm` y el manifiesto. La etiqueta "Diaria" del catálogo de `bureau-clima` no se cumple.
3. **La pieza de prensa no se publica.** `prensa_medios.json` está en `PIEZAS`, pero no existe en `etl-bureau/export/tableros_bureau/` de `main`. Por eso el manifiesto del tablero trae seis `prensa: HTTP Error 404`, y `bureau_prensa.json` quedó con `url: file:///tmp/tbout2/prensa_medios.json`.
4. **Las piezas propias del tablero también son manuales.** `conectividad`, `ema`, `evi`, `huella`, `icca` y `medata_tarifas` salen de `scripts/preparar_fuentes.py` y tienen fecha de descarga 24-oct. La conectividad del tablero llega a junio de 2026, aunque el ETL baja diario el mismo dataset Aerocivil `gb6w-ynu4`.
5. **El catálogo no coincide con lo que se muestra.** La ficha `busqueda` sigue citando Wikimedia y GDELT. `data/open/wikipedia.json` quedó huérfano: `app.js` no lo lee desde que la señal digital pasó a prensa.
6. **Hay fuentes en el ETL que hoy no aportan nada:**
   - `gdelt_marca`: 429 del DOC API, 0 filas.
   - `gastronomia_nocturna` (OSM): Overpass devuelve 406 o timeout, 0 filas.
   - `airportmiles_mde`: 0 filas.
   - `emisores_contexto`: 404 en la fuente principal y en el respaldo, 0 filas.
   - `tieredtravel_med`: 0 coincidencias para Medellín.
   - `eurostat_demanda`: `tour_dem_ttot` y `tour_dem_toac` dan 404; solo queda `ttmd`.
   - `dane_enh`: ningún anexo vivo.
   - `aerocivil_flota` con `w9ei-uhm3`: 400 por `$order=a_o`.
   - Alumbrados con `5upz-u2vi`: 400 en el filtro de Sabaneta.
7. **Hay duplicados y proxies que ya tienen fuente oficial.** `trm_co` (ER-API) y `fx_cop` (currency-api) son dos proxies de la misma tasa; la TRM oficial está en datos.gov.co (ver 3.1). `un_wb_arrivals`, `wb_receipts` y `wb_departures` no traen datos después de 2020, porque el Banco Mundial ya no actualiza esos indicadores; OWID ya los reemplazó en el tablero.

---

## 2. Inventario ordenado por pestaña del tablero

### 2.1 Mercados

| Indicador (id catálogo) | Fuente primaria | Dataset / endpoint | Script que lo produce | Pieza `data/open` | Corte visible | Estado |
|---|---|---|---|---|---|---|
| Conectividad aérea (`conectividad`) | Aerocivil, tráfico origen-destino | datos.gov.co `gb6w-ynu4` | `tableros-bureau/scripts/preparar_fuentes.py` | `conectividad.json` | 2026-06 | Foto manual (24-oct) |
| Reservas, proxy llegadas (`reservas`) | Aerocivil | `gb6w-ynu4` | ídem | `conectividad.json` | 2026-06 | Foto manual |
| Intención / share of voice (`busqueda`) | Google News RSS + Reddit (antes Wikimedia/GDELT) | RSS | `extract/alerts_rss.py`, `export/tableros_bureau_llm.py` | `bureau_prensa.json` | 2026-W45 | Roto (404 al publicar) |
| Conversación por tema (`marca-llm`) | alerts_rss + prensa_rss clasificados con Groq | RSS El Colombiano, Alcaldía, MinCIT, Google News | `classify/llm_classify.py` → adapter | `bureau_marca_llm.json` | 2026-10/11 | Diaria (cuando el daily corre) |
| Emisores por país (`bureau-paises`) | Migración Colombia + Aerocivil | `96sh-4v8d`, `7wm8-w5ad`, `efw5-jiej`, `gb6w-ynu4` | `extract/socrata_co.py` → `transform/kpis.py` → adapter | `bureau_paises_2025_2026.json` | 2025–2026 YTD | Diaria |
| ICCA (`icca`) | ICCA GlobeWatch 2025 (PDF difundido) | PDF | `preparar_fuentes.py` | `icca.json` | 2025 | Cita anual |
| Tarifas de alojamiento (`tarifas`) | DANE EMA + MEData tarifa por zona | `anex-EMA-ago2026.xlsx`; MEData nodo 16279 | `preparar_fuentes.py` | `ema.json`, `medata_tarifas.json` | EMA 2026-08; MEData 2023-12 (congelado) | Foto manual |
| Conversión de mercados (`conversion`) | CRM del Bureau | `data/raw/manual/crm.xlsx` (5 filas de ejemplo) | `extract/gated_icca.py` | simulador | — | Pendiente |
| Conectividad y benchmarks (`bureau-conectividad`) | Aerocivil, terminales, Metro, TRM, Eurostat, Wikimedia | `djjf-g4q4`, `w9ei-uhm3`, `aesn-q83n`, `a45t-7a3r`, MEData Metro, Eurostat `tour_occ_*`, `avia_paoc` | `export/bureau_conectividad.py` | `bureau_conectividad.json` | operaciones 2026-07 | Foto manual |
| Benchmark mundial (`bureau-owid`) | Our World in Data (UN Tourism) | grapher `international-tourist-trips` | `export/bureau_owid.py` | `bureau_owid.json` | 2024 (Colombia 2022) | Foto manual |
| Perfiles emisores SIT (`bureau-sit`) | SIT Medellín, 5 informes de mercado | PDFs | `export/bureau_sit.py` | `bureau_sit.json` | 2025 | Cita |

### 2.2 Visitante

| Indicador | Fuente primaria | Dataset / endpoint | Script | Pieza | Corte | Estado |
|---|---|---|---|---|---|---|
| Gasto promedio (`gasto`) | DANE EVI microdatos | catálogo 869 | `preparar_fuentes.py` | `evi.json` | ola ene–jun 2025 | Foto manual |
| Grupo y estadía (`grupo`) | DANE EVI | catálogo 869 | ídem | `evi.json` | ene–jun 2025 | Foto manual |
| Perfil y motivos (`perfil`) | DANE EVI | catálogo 869 | ídem | `evi.json` | ene–jun 2025 | Foto manual |
| NPS del destino (`nps`) | Encuesta Bureau / SIT | — | — | simulador | — | Pendiente |
| Huella de carbono (`huella`) | EVI + OurAirports + factores DESNZ UK 2026 | `airports.csv`, xlsx gov.uk | `preparar_fuentes.py` | `huella.json` | ene–jun 2025 | Foto manual |
| Oferta y territorio (`bureau-oferta`) | RNT MinCIT + DANE EGIT | `thwd-ivmp`, `anex-EGIT-IItrim2026.xlsx` | `export/bureau_oferta.py` | `bureau_oferta.json` | RNT 2026-10; EGIT II-2026 | Foto manual |
| Seguridad ciudadana (`bureau-seguridad`) | SIEDCO Policía Nacional | `4rxi-8m8d` (hurtos), `m8fd-ahd9` (homicidios) | `export/bureau_seguridad.py` | `bureau_seguridad.json` | 2026-09 | Foto manual |
| Clima y aire (`bureau-clima`) | IDEAM + Open-Meteo | `57sv-p2fu`, `hp9r-jxuu`, `s54a-sgyg`; Open-Meteo forecast, air-quality y ensemble | `export/bureau_clima.py` | `bureau_clima.json` | lluvia 2026-08 (1 fila) | Foto manual, serie casi vacía |
| Calendario y contexto (`bureau-calendario`) | Nager.at festivos CO + IDEAM estaciones | `date.nager.at/api/v3/publicholidays/{y}/CO` | `export/bureau_calendario.py` | `bureau_calendario.json` | 2025–2026 | Foto manual |

### 2.3 Captación B2B y Miembros

Todo sale del informe de gestión 2025 del Bureau (`data/informe2025.js`), como cita, o queda pendiente del CRM o del libro de miembros:

- Cita del informe: `roi`, `flujo`, `engagement`, `oportunidades`, `satisfaccion`.
- Derivada de Aerocivil y EVI: `scoring`.
- Pendiente de extracto primario: `inspeccion`, `perdidas`, `valor`, `retencion`.

Ninguna fuente abierta reemplaza estos indicadores; hace falta un extracto del CRM o del libro de miembros (sección 3.3).

### 2.4 Informes

| Pieza | Fuente | Script | Corte | Estado |
|---|---|---|---|---|
| `informe_llm.json` | Warehouse PROC redactado con Groq y verificado cifra por cifra | `report/redactar_informe.py` | 2026-11-01 | Diaria; se rechaza si una cifra no tiene fuente |

### 2.5 Fuentes del ETL que hoy no llegan a ningún panel

| Extractor | Fuente | Estado hoy | Recomendación |
|---|---|---|---|
| `google_trends` | pytrends | 465 filas | Exponer en Mercados como intención por mercado, o retirarlo. La ficha `busqueda` dice que no se usa. |
| `un_wb_arrivals`, `wb_receipts`, `wb_departures` | Banco Mundial `ST.INT.*` | Sin datos después de 2020 | Retirar; OWID ya cubre llegadas. |
| `eurostat_tourism`, `eurostat_arrivals`, `eurostat_capacity`, `eurostat_aviation` | Eurostat | OK | Siguen dentro de la foto de conectividad; publicarlos con el daily. |
| `eurostat_demanda` | Eurostat `tour_dem_*` | 2 de 3 datasets dan 404 | Dejar solo `tour_dem_ttmd`. |
| `medata` | MEData Alcaldía | OK, series congeladas en 2023 | Mantener como línea base histórica (ocupación por temporada, PITS). |
| `dane_egit` | DANE EGIT | OK | Ya alimenta la oferta; publicar con el daily. |
| `rnt_antioquia` | RNT `mmsn-v5r4` | OK | Sumar a la oferta regional. |
| `openmeteo_med`, `aire_med`, `openmeteo_ensemble`, `ideam_clima` | Open-Meteo / IDEAM | OK | Publicar `bureau_clima` diario; hoy la foto tiene 1 fila. |
| `trm_co`, `fx_cop` | ER-API / currency-api | OK, proxies duplicados | Reemplazar COP por la TRM oficial (3.1); dejar `fx_cop` solo para EUR, MXN y BRL. |
| `festivos_co` | Nager.at | OK | Extender a los mercados emisores (3.1). |
| `wikimedia_views` | Wikimedia | OK | Huérfano en el tablero; decidir si vuelve como señal digital. |
| `metro_movilidad`, `terminales_med` | MEData / Socrata | OK | Ya están en la foto de conectividad. |
| `gdelt_marca` | GDELT DOC API | 429, 0 filas | Cambiar a los archivos crudos de GDELT 2.0 (3.1) o retirarlo. |
| `gastronomia_nocturna` | Overpass OSM | 406 o timeout, 0 filas | Enviar `Accept: */*` y la consulta por POST, o usar un extracto Geofabrik de Colombia mensual. |
| `airportmiles_mde`, `emisores_contexto`, `tieredtravel_med` | public-apis tanda 1 | 0 filas | Retirar. |
| `conectividad_aerea` | OurAirports + OpenFlights | Comentado en `sources.yml` | OpenFlights no se actualiza desde 2014; retirar. |

---

## 3. Fuentes nuevas propuestas

Cada candidata dice qué indicador del tablero o del Plan Dashboard alimenta. Las de la sección 3.1 se probaron el 2-nov-2026 desde este entorno.

### 3.1 Prioridad 1: abiertas, sin key, verificadas hoy

| # | Fuente | Endpoint | Prueba 2-nov | Alimenta |
|---|---|---|---|---|
| 1 | **TRM oficial (Superfinanciera)** | `https://www.datos.gov.co/resource/32sa-8pi3.json` | 200, TRM 3.182,99 vigente 31-oct a 3-nov | Derrama COP/USD y pricing MICE. Reemplaza `trm_co` y el COP de `fx_cop`. |
| 2 | **Calidad del aire SISAIRE, estaciones AMVA** | `https://www.datos.gov.co/resource/g4t8-zkc3.json?nombre_fgda=AMVA` | 200, estaciones de Medellín, último dato 2025-12-31 | `bureau-clima`: PM2.5 medido en estación al lado del modelado de Open-Meteo. Tiene rezago; usarlo para histórico. |
| 3 | **Advertencia de viaje de EE. UU. (State Dept)** | `https://cadataapi.state.gov/api/TravelAdvisories` | 200, Colombia nivel 3 "Reconsider Travel", actualizado 30-mar-2026 | KPI Marca "Percepción de seguridad (objeción n.º 1)" vista desde el mercado emisor n.º 1. |
| 4 | **Advertencia de viaje de Canadá** | `https://data.international.gc.ca/travel-voyage/cta-cap-co.json` | 200, `advisory-state 1`, con aviso regional | Ídem; mercado norteamericano. |
| 5 | **Advertencia de viaje del Reino Unido (FCDO)** | `https://www.gov.uk/api/content/foreign-travel-advice/colombia` | 200 | Ídem; mercado europeo. Trae fecha de cambio y resumen. |
| 6 | **Festivos de los mercados emisores** | `https://date.nager.at/api/v3/publicholidays/{año}/{US,MX,BR,ES,PA,FR,DO}` | 200 (US 2026) | Calendario: ventanas de viaje de cada emisor para programar pauta. Es extender `festivos_co`. |
| 7 | **GDELT 2.0, archivos crudos cada 15 min** | `https://data.gdeltproject.org/gdeltv2/lastupdate.txt` | 200, último archivo 2026-11-03 03:15 UTC | Share of voice y sentimiento sin el límite 429 del DOC API. El GKG pesa unos 3,7 MB cada 15 min: muestrear o usar BigQuery. |
| 8 | **CEPALSTAT API** | `https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/{id}/data` | 200 (API viva) | Benchmark LatAm de llegadas e ingresos por turismo. Falta fijar los IDs de los indicadores de turismo. |
| 9 | **Banco Central do Brasil, SGS** | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados` | 200 (API viva) | Gasto mensual de brasileños en viajes al exterior (mercado priorizado Brasil). Confirmar el código de la serie "viagens internacionais – despesas". |
| 10 | **INE España, API Tempus** | `https://servicios.ine.es/wstempus/js/ES/...` | 200 (API viva) | Residentes en España que viajan al exterior (ETR/FRONTUR): demanda del emisor europeo. Fijar la tabla. |
| 11 | **Países que requieren visa para ingresar a Colombia** | `https://www.datos.gov.co/resource/g7ps-wzb3.json` | 200 | Contexto de facilidad de entrada por mercado en `bureau-sit` / scoring. |
| 12 | **BTS T-100 International Segment (EE. UU.)** | transtats.bts.gov, descarga por formulario | Página viva | Asientos, salidas y pasajeros de las rutas EE. UU.–MDE. Cubre el "no mide asientos ofrecidos" de `conectividad`. Descarga mensual. |
| 13 | **DANE IPC por ciudad** (alojamiento, restaurantes, paquetes) | anexos IPC dane.gov.co | Página viva | `tarifas`: precio de alojamiento en Medellín frente a otras ciudades, mensual. Reemplaza a MEData, congelado en 2023. |
| 14 | **DANE EMA mensual (reponer)** | `anex-EMA-{mes}{año}.xlsx` | Ya probada 24-oct | `tarifas` y ocupación. Hoy es foto manual y el módulo `dane_ema` falta. |

Probadas y descartadas hoy:

- Inside Airbnb no publica Medellín.
- Xotelo exige RapidAPI.
- La API del FMI (DataMapper) responde 403 desde un runner.
- OpenSky anónimo responde 403; ahora requiere cuenta (pasa a 3.2).
- El dataset datos.gov.co `uxa3-q5bz` "Servicios de turismo" no es de Medellín.

### 3.2 Prioridad 2: gratis con registro o key

Las keys van como secret del workflow, igual que `GROQ_API_KEY`.

| Fuente | Qué aporta | Alimenta |
|---|---|---|
| Ticketmaster Discovery API | Agenda de eventos en Medellín (el módulo falta en el repo) | Calendario MICE y uplift por evento |
| Tripadvisor Content API (cuota gratuita mensual) | Rating y número de reseñas de atracciones y hoteles | `nps`: proxy de satisfacción del destino (el Plan lo pide: "TripAdvisor rating medio") |
| Google Places API (crédito mensual gratis) | Rating de recintos MICE y de atractivos | `nps` y calidad de sede |
| YouTube Data API v3 | Vistas y publicaciones sobre Medellín, canal del Bureau | Marca: alcance |
| Travelpayouts / Aviasales Data API (token gratis) | Precio de tarifa aérea por ruta desde los emisores | Competitividad de acceso por mercado |
| OpenSky (cuenta gratis, OAuth) | Llegadas y salidas reales MDE/EOH (el módulo falta) | Conectividad en vivo |
| Banxico SIE (token gratis) | Viajeros internacionales mexicanos | Mercado México |
| Media Cloud (cuenta gratis) | Cobertura de medios con histórico | Share of voice, alternativa a GDELT y Brand24 |
| Google Search Console + GA4 de medellin.travel y visitmedellin.co (credenciales del Bureau) | Tráfico orgánico, keywords y conversión | KPIs de Marca del Plan: "Ser encontrados" y "Convertir digital" |
| Meta Graph API e Instagram Insights (cuentas del Bureau) | Engagement de las cuentas propias | Marca: "Comunidad activa" |
| Amadeus for Developers | Ofertas de vuelo y hotel | Verificar que el portal Self-Service siga vigente; el endpoint de prueba no respondió hoy |

### 3.3 Prioridad 3: primarias, convenio o pago

Desbloquean los indicadores que hoy están "Pendiente".

| Fuente | Indicadores que desbloquea |
|---|---|
| CRM de captación del Bureau (RFP, inspecciones, motivos de pérdida, aporte Wompi) | `conversion`, `inspeccion`, `perdidas`, `roi`, `flujo` |
| Libro de miembros (padrón de apertura, cuota, bajas) | `valor`, `retencion` |
| Encuesta post-evento y encuesta de destino del Bureau | `nps` y satisfacción del organizador |
| SIT Medellín / SITUR Antioquia, microdatos por convenio | Gasto, estadía y NPS del visitante; reemplaza la EVI semestral |
| Cotelco o STR (ocupación y ADR por semana) | `tarifas`, ocupación incremental por evento |
| Airplan (JMC/EOH) y Aerocivil: sillas ofrecidas | Conectividad con capacidad, no solo pasajeros |
| Plaza Mayor: agenda y ocupación de recintos | Calendario MICE |
| ICCA membresía / UFI | Participación ICCA y no ICCA trimestral |
| GlobalData, Brand24, OAG/Cirium (pago) | Solo si el Bureau compra; se cargan como manuales en `data/raw/manual/` |

---

## 4. Orden de trabajo sugerido

1. Restaurar el daily: subir los 10 módulos faltantes o quitar sus imports en `orchestration/daily.py`.
2. Meter los 7 exportadores `bureau_*` en el daily y en `PIEZAS` de `publicar.py`. Corregir la publicación de `prensa_medios.json`.
3. Programar `preparar_fuentes.py` (tableros-bureau) en un workflow mensual, para que conectividad, EMA y EVI dejen de ser fotos.
4. Limpiar las fuentes rotas o duplicadas de la sección 2.5 y alinear `data/catalog.js` (ficha `busqueda`, `wikipedia.json` huérfano).
5. Sumar las fuentes de prioridad 1, en este orden: TRM oficial; advertencias de viaje de EE. UU., Canadá y Reino Unido; festivos de los emisores; SISAIRE; DANE IPC y EMA; BTS T-100.
6. Gestionar con el Bureau las keys de prioridad 2 y los extractos de prioridad 3.
