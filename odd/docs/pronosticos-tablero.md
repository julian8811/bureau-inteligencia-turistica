# Pronóstico a 6 meses

Corte entrenado el 3 de noviembre de 2026 (hora de Bogotá). Las cifras de este texto son las de `etl-bureau/export/tableros_bureau/pronosticos.json`. El tablero las lee en Mercados y en Visitante, grupo Pronóstico.

## Qué se incorporó de turismo-analytics-2026

De [turismo-analytics-2026](https://github.com/julian8811/turismo-analytics-2026) entra la serie mensual que se puede verificar, no el catálogo ni los modelos que ese ejercicio corona por MAPE a 12 meses.

- Ocupación nacional de la EMA, enero de 2019 a agosto de 2026 (92 meses). Agosto: 49,21 %.
- Ocupación de Antioquia alargada a esos mismos 92 meses. Agosto: 51,45 %. Desde 2022 coincide con la serie corta del tablero; si un anexo futuro no coincide, se queda la corta.
- Ingresos reales de alojamiento, índice nacional base 2019=100, desde enero de 2015 (140 meses). Agosto: 89,08. No es la tarifa de Antioquia (agosto 161,96) ni el IPC.
- TRM promedio mensual de la Superfinanciera (datos.gov.co `32sa-8pi3`), enero de 2015 a octubre de 2026 (142 meses). Octubre: 3.198,62. El daily sigue publicando la tasa del día. Son dos series.

No entra Prophet (pide CmdStan), ni Chronos-Bolt, ni el ensamble ponderado por 1/MAPE, ni un SARIMAX que use log(TRM) como causa de la ocupación. En el backtest de 12 meses de ese repo ese SARIMAX quedó último. La TRM se pronostica sola. Tampoco entran notas, PDF ni el resto del catálogo de 55 fuentes: no son una serie mensual verificada.

El SARIMA de este ETL, en esa misma ventana de 12 meses y sin cambiar lo que sale en el tablero, repite el MAPE de aquel repo: ocupación nacional 3,81 %, Antioquia 6,30 %, ingresos reales 7,00 %.

Con la regla de este tablero, esa ventana de 12 meses no coronaría el mismo modelo que el semestre. Antioquia publicaría el mes anterior (MAE 2,66). La ocupación nacional publicaría el gradiente (MAE 1,49; el mes anterior queda en 1,52). Los ingresos publicarían el mes anterior (MAE 6,23). El LightGBM de aquí usa solo rezagos, así que no es el de 300 árboles de aquel repo y no gana esa ventana. Lo que se publica sigue siendo el ensayo de 6 meses. La nota de cada serie lo dice.

## Qué más quedó fuera

Hacen falta meses, no un modelo más grande. Llegadas Aerocivil de los cinco mercados: 54 meses, enero de 2022 a junio de 2026. Tarifa de Antioquia: 56 meses, hasta agosto de 2026. Homicidios y hurtos de Medellín (SIEDCO): la serie de homicidios queda en 96 meses porque julio, agosto y septiembre de 2018 vienen en 0.

Quedaron fuera, y el tablero lo dice:

- Operaciones aéreas (31 meses), BTS T-100 (24) e IPC nacional (33). Cortos para un ensayo de 6 meses y un ciclo de 12.
- El agregado de países y OWID Colombia. Son anuales. OWID además corta en 2022.
- SISAIRE (11 días, cierra el 31 de diciembre de 2025) y la lluvia del corte (un mes).
- La EVI, que es una ola semestral.
- La TRM de un día. El pronóstico usa el promedio mensual.

Tampoco entra el CRM, ni las reservas, ni una causa. El modelo solo prolonga la serie que ya se ve.

## Cómo se elige

Cinco pronósticos, a 6 meses. Holt-Winters, SARIMA, el gradiente y LightGBM se alimentan de su propio pronóstico cuando hace falta:

1. Repetir el mismo mes del año anterior.
2. Holt-Winters aditivo, periodo 12 (`statsmodels`).
3. SARIMA(1,0,1)(1,1,0)12. Si la serie cruza marzo de 2020 a diciembre de 2021 y el indicador no es constante, lleva un regresor: 1 de marzo de 2020 a junio de 2021, 0,5 de julio a diciembre de 2021 y 0 en el horizonte. Las llegadas empiezan en 2022 y no lo llevan.
4. Gradiente con tres rasgos: el mes anterior, el mismo mes del año pasado y el mes de calendario (`HistGradientBoostingRegressor`, profundidad 3, 100 iteraciones, semilla 0).
5. LightGBM con rezagos 1, 2, 3 y 12 (200 árboles, 8 hojas, semilla 0).

El ensayo es el último semestre observado. Gana el menor error absoluto (MAE). Si otro modelo queda a menos del 2 % de ese mínimo, se publica el más simple, en el orden de la lista. El MAPE no decide.

La banda es el percentil 80 de ese error absoluto. No es un intervalo de confianza. Pasajeros, homicidios, hurtos y la TRM no bajan de 0. La ocupación queda entre 0 y 100.

Antes de entrenar, un punto menor al 15 % de la mediana y al 20 % de sus dos vecinos se reemplaza por el promedio de esos vecinos. En estas series solo ocurre una vez: Brasil, mayo de 2022, registró 1 llegada entre 675 y 373. Entra 524. La suma de los cinco mercados usa ese valor, no el 1.

## Resultado

Sobre las 13 series, el ensayo publica Holt-Winters en 5, SARIMA en 6 y el gradiente en 2. LightGBM no queda publicado: cuando se acerca, el modelo más simple está dentro del 2 % o le gana.

| Serie | Corte | N | Publicado | MAE | MAPE | MAE del mes anterior | Banda |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| Llegadas Colombia | 2026-06 | 54 | Holt-Winters | 19.440,5 | 4,5 % | 29.269,3 | ±37.139 |
| Llegadas Estados Unidos | 2026-06 | 54 | SARIMA | 4.663,7 | 8,9 % | 5.043,7 | ±4.072 |
| Llegadas México | 2026-06 | 54 | SARIMA | 1.068,8 | 7,3 % | 1.244,2 | ±1.967 |
| Llegadas Brasil | 2026-06 | 54 | SARIMA | 394,8 | 47,8 % | 771,5 | ±562 |
| Llegadas Europa | 2026-06 | 54 | Gradiente | 645,8 | 5,6 % | 1.338,0 | ±966 |
| Suma de los cinco | 2026-06 | 54 | Holt-Winters | 29.707,8 | 5,9 % | 35.693,0 | ±47.993 |
| TRM promedio mensual | 2026-10 | 142 | Holt-Winters | 373,98 | 11,6 % | 702,21 | ±563,71 |
| Ocupación Antioquia | 2026-08 | 92 | Gradiente | 2,24 | 4,8 % | 3,51 | ±3,24 |
| Tarifa Antioquia | 2026-08 | 56 | SARIMA | 1,83 | 1,1 % | 8,04 | ±1,90 |
| Ocupación nacional | 2026-08 | 92 | SARIMA | 1,59 | 3,4 % | 1,95 | ±3,16 |
| Ingresos reales | 2026-08 | 140 | Holt-Winters | 3,52 | 4,1 % | 8,06 | ±4,51 |
| Homicidios Medellín | 2026-09 | 96 | Holt-Winters | 7,3 | 84,2 % | 10,7 | ±15 |
| Hurtos Medellín | 2026-09 | 99 | SARIMA | 322,3 | 22,7 % | 449,7 | ±416 |

MAE y banda están en la unidad de la serie. El MAPE no decide.

Colombia y la suma de los cinco siguen en Holt-Winters. Diciembre de 2026 sale en 461.554 llegadas desde Colombia (rango 424.415 a 498.693) y la suma en 566.787 (rango 518.794 a 614.780). Son llegadas realizadas de Aerocivil, no reservas y no el cupo del aeropuerto.

Estados Unidos: SARIMA baja el MAE de 5.043,7 a 4.663,7. Septiembre de 2026 sale en 39.554, con rango 35.482 a 43.626. Holt-Winters (7.194,2) y el gradiente (5.708,0) quedan por detrás del mes anterior; SARIMA no.

México: SARIMA baja el MAE de 1.244,2 a 1.068,8. Holt-Winters solo llegaba a 1.228,2, dentro del 2 % del mes anterior, y por eso antes se publicaba el mes anterior. Con SARIMA el margen ya no alcanza y el publicado cambia.

Europa: el gradiente sigue adelante (645,8 contra 836 de SARIMA, 851,5 de Holt-Winters y 1.338 del mes anterior). Octubre, noviembre y diciembre salen en el mismo número, 13.669. El árbol, al alimentarse de su propio pronóstico, deja de mover la serie. El error del ensayo fue menor; la cola plana no es una aceleración del mercado.

Brasil: SARIMA gana el MAE (394,8 contra 503,7 del gradiente y 771,5 del mes anterior) y el MAPE queda en 47,8 %. La banda de ±562 pasajeros es amplia frente a las 1.354 llegadas de junio de 2026. Julio sale en 1.141 y el piso del rango es 579. No es una meta de mercadeo.

TRM: Holt-Winters baja el MAE de 702,21 a 373,98 pesos. LightGBM queda en 374,07, peor que Holt-Winters. Noviembre de 2026 sale en 3.237,78. No es la tasa de un día ni una causa de las llegadas.

Ocupación de Antioquia: el gradiente, ya con los 92 meses, baja el error de 3,51 a 2,24 puntos. De 51,45 % en agosto el punto va a 51,23 % en septiembre y a 49,59 % en febrero de 2027, banda ±3,24. Es la región, no la ciudad de Medellín. En los 12 meses la misma regla publicaría el mes anterior.

Ocupación nacional: SARIMA baja el MAE de 1,95 a 1,59. Septiembre sale en 47,73 % (agosto cerró en 49,21 %), banda ±3,16. No es Antioquia ni un hotel. En los 12 meses la regla publicaría el gradiente.

Ingresos reales: Holt-Winters baja el MAE de 8,06 a 3,52. De 89,08 en agosto el punto va a 86,20 en septiembre y a 102,36 en diciembre, banda ±4,51. No es la tarifa ni el IPC. En los 12 meses la regla publicaría el mes anterior.

Tarifa de Antioquia: SARIMA queda en 1,83 (MAPE 1,1 %) y el gradiente en 1,86. Septiembre sale en 159,37 y febrero de 2027 en 173,41, banda ±1,90. El mes anterior se queda atrás (MAE 8,04) porque el nivel viene subiendo.

Homicidios: Holt-Winters baja el MAE de 10,7 a 7,3 casos, pero el MAPE sigue en 84 % y la banda es ±15 frente a un septiembre que cerró en 5. Octubre sale en 12 con rango de 0 a 27. Ganarle al mes anterior no lo vuelve un pronóstico útil. No es una tasa por habitante.

Hurtos: el gradiente tiene MAE 321,2 y SARIMA 322,3. Están a menos del 2 % y se publica SARIMA, que es el más simple de los dos. La banda de ±416 casos sobre 1.162 de septiembre también es amplia. Octubre sale en 1.629, rango 1.213 a 2.045. No está partido por zona.

## Dónde está en el tablero

Mercados y Visitante tienen un grupo Pronóstico. Los botones cambian la serie. En Mercados están los cinco orígenes, la suma y la TRM mensual. En Visitante, las dos ocupaciones, la tarifa, los ingresos reales, los homicidios y los hurtos. La línea continua es el observado (18 meses) y la punteada es el pronóstico (6). La tabla muestra los cinco MAE. La ficha `bureau-pronostico` dice qué no mide.

Este token no puede publicar en `tableros-bureau`. El cambio de pantalla va en tres parches, en este orden:

```
git am odd/docs/tableros-bureau-fuentes.patch
git am odd/docs/tableros-bureau-pronostico.patch
git am odd/docs/tableros-bureau-ema.patch
```

El JSON de producción lo trae `scripts/alimentar_bureau.py` desde `pronosticos.json` cuando este archivo ya está en `main` del ETL. El parche deja una copia en `data/open/bureau_pronostico.json` para que el tablero se vea antes de ese pull.

El daily del ETL corre `models/pronosticar.py` después de exportar seguridad y antes de publicar. Si el anexo EMA está en `data/raw`, alarga la ocupación y suma las series nuevas. Si está el CSV `trm_mensual.csv`, usa ese promedio. Si faltan, usa `models/insumos/series_mensuales.json`. Si falta una librería, esa familia no compite y el texto lo dice. Si el entrenamiento falla, no borra el JSON anterior.
