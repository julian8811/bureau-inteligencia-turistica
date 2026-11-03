# Pronóstico a 6 meses

Corte entrenado el 2 de noviembre de 2026 (hora de Bogotá). Las cifras de este texto son las de `etl-bureau/export/tableros_bureau/pronosticos.json`. El tablero las lee en Mercados y en Visitante, grupo Pronóstico.

## Qué se entrenó y qué no

Hacen falta meses, no un modelo más grande. Llegadas Aerocivil de los cinco mercados: 54 meses, enero de 2022 a junio de 2026, sin huecos. Ocupación y tarifa hotelera de Antioquia (EMA): 56 meses, hasta agosto de 2026. Homicidios y hurtos de Medellín (SIEDCO): 99 meses, julio de 2018 a septiembre de 2026. Con eso se puede repetir la estacionalidad y comparar dos modelos clásicos. No alcanza para una red.

Quedaron fuera, y el tablero lo dice:

- Operaciones aéreas (31 meses), BTS T-100 (24) e IPC nacional (33). Cortos para un ensayo de 6 meses y un ciclo de 12.
- El agregado de países y OWID Colombia. Son anuales. No se inventan meses. OWID además corta en 2022.
- SISAIRE (11 días, cierra el 31 de diciembre de 2025), la TRM oficial (ventana de días) y la lluvia del corte (un mes).
- La EVI, que es una ola semestral.

Tampoco entra el CRM, ni las reservas, ni una causa. El modelo solo prolonga la serie que ya se ve.

## Cómo se elige

Tres pronósticos, a 6 meses, recursivos cuando el modelo se alimenta de sí mismo:

1. Repetir el mismo mes del año anterior.
2. Holt-Winters aditivo, periodo 12 (`statsmodels`).
3. Gradiente con tres rasgos: el mes anterior, el mismo mes del año pasado y el mes de calendario (`HistGradientBoostingRegressor`, profundidad 3, 100 iteraciones, semilla 0).

El ensayo es el último semestre observado. Gana el menor error absoluto (MAE). Si otro modelo queda a menos del 2 % de ese mínimo, se publica el más simple: el mes anterior, después Holt-Winters, después el gradiente. Así un modelo que no le gana al calendario no sale coronado.

La banda es el percentil 80 de ese error absoluto. No es un intervalo de confianza. Pasajeros, homicidios y hurtos no bajan de 0. La ocupación queda entre 0 y 100.

Antes de entrenar, un punto menor al 15 % de la mediana y al 20 % de sus dos vecinos se reemplaza por el promedio de esos vecinos. En estas series solo ocurre una vez: Brasil, mayo de 2022, registró 1 llegada entre 675 y 373. Entra 524. La suma de los cinco mercados usa ese valor, no el 1. Los homicidios de julio, agosto y septiembre de 2018 vienen en 0 con hurtos positivos; se tratan como dato ausente y la serie queda en 96 meses.

## Resultado

Sobre las 10 series, el ensayo publica el mes anterior en 2, Holt-Winters en 4 y el gradiente en 4.

| Serie | Corte | N | Publicado | MAE | MAPE | MAE del mes anterior | Banda |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| Llegadas Colombia | 2026-06 | 54 | Holt-Winters | 19.440,5 | 4,5 % | 29.269,3 | ±37.139 |
| Llegadas Estados Unidos | 2026-06 | 54 | Mes anterior | 5.043,7 | 9,1 % | 5.043,7 | ±7.415 |
| Llegadas México | 2026-06 | 54 | Mes anterior | 1.244,2 | 8,3 % | 1.244,2 | ±1.844 |
| Llegadas Brasil | 2026-06 | 54 | Gradiente | 503,7 | 40,3 % | 771,5 | ±733 |
| Llegadas Europa | 2026-06 | 54 | Gradiente | 645,8 | 5,6 % | 1.338,0 | ±966 |
| Suma de los cinco | 2026-06 | 54 | Holt-Winters | 29.707,8 | 5,9 % | 35.693,0 | ±47.993 |
| Ocupación Antioquia | 2026-08 | 56 | Holt-Winters | 2,38 | 5,1 % | 3,51 | ±2,69 |
| Tarifa Antioquia | 2026-08 | 56 | Gradiente | 1,86 | 1,2 % | 8,04 | ±2,17 |
| Homicidios Medellín | 2026-09 | 96 | Holt-Winters | 7,3 | 84,2 % | 10,7 | ±15 |
| Hurtos Medellín | 2026-09 | 99 | Gradiente | 321,2 | 21,2 % | 449,7 | ±452 |

MAE y banda están en la unidad de la serie (pasajeros, puntos de ocupación, puntos del índice o casos). El MAPE no decide.

Estados Unidos: Holt-Winters (7.194,2) y el gradiente (5.708,0) pierden contra repetir el mes. El publicado es el mes anterior. Septiembre queda en 36.960 porque septiembre de 2025 fue así; el modelo no suaviza ese valle.

México: Holt-Winters baja el MAE de 1.244,2 a 1.228,2, un 1,3 %. Está dentro del 2 % y se deja el mes anterior. El gradiente queda peor (1.600,7).

Colombia y la suma de los cinco: Holt-Winters sí se separa. Colombia baja de 29.269 a 19.441 pasajeros de error (MAPE 4,5 %). Diciembre de 2026 sale en 461.554, con rango 424.415 a 498.693. La suma sale en 566.787 en diciembre, rango 518.794 a 614.780. Son llegadas realizadas de Aerocivil, no reservas y no el cupo del aeropuerto.

Europa: el gradiente gana (646 contra 852 y 1.338) pero octubre, noviembre y diciembre salen en el mismo número, 13.669. El árbol, al alimentarse de su propio pronóstico, deja de mover la serie. El error del ensayo fue menor; la cola plana no es una aceleración del mercado.

Brasil: el gradiente gana el MAE (504 contra 532 y 772) y aun así el MAPE queda en 40 %. La banda de ±733 pasajeros es amplia frente a las 1.354 llegadas de junio de 2026. Julio sale en 653 y el piso del rango es 0. No es una meta de mercadeo. La serie cambia de nivel a finales de 2024 y un semestre de ensayo no alcanza para fiarse del punto.

Ocupación: es Antioquia en la EMA, no la ciudad de Medellín. Holt-Winters baja el error de 3,51 a 2,38 puntos. De 51,45 % en agosto de 2026 el punto va a 46,51 % en septiembre y a 43,50 % en febrero de 2027, con una banda de ±2,69 puntos.

Tarifa: el índice de Antioquia, no el IPC ni la tarifa de un hotel. El mes anterior se queda atrás (MAE 8,04) porque el nivel viene subiendo. El gradiente queda en 1,86 (MAPE 1,2 %). Septiembre de 2026 sale en 159,89 y febrero de 2027 en 161,95, banda ±2,17.

Homicidios: Holt-Winters baja el MAE de 10,7 a 7,3 casos, pero el MAPE sigue en 84 % y la banda es ±15 frente a un septiembre que cerró en 5. Octubre sale en 12 con rango de 0 a 27. Ganarle al mes anterior no lo vuelve un pronóstico útil. No es una tasa por habitante.

Hurtos: el gradiente baja el MAE de 450 a 321 y Holt-Winters queda peor que el mes anterior (491). La banda de ±452 casos sobre 1.162 de septiembre también es amplia. Octubre sale en 960, rango 508 a 1.412. No está partido por zona.

## Dónde está en el tablero

Mercados y Visitante tienen un grupo Pronóstico. Los botones cambian la serie. La línea continua es el observado (18 meses) y la punteada es el pronóstico (6). La tabla muestra los tres MAE. La ficha `bureau-pronostico` dice qué no mide.

Este token no puede publicar en `tableros-bureau`. El cambio de pantalla va en `odd/docs/tableros-bureau-pronostico.patch`, encima de `odd/docs/tableros-bureau-fuentes.patch`. En un clon del tablero:

```
git am odd/docs/tableros-bureau-fuentes.patch
git am odd/docs/tableros-bureau-pronostico.patch
```

El JSON de producción lo trae `scripts/alimentar_bureau.py` desde `pronosticos.json` cuando este archivo ya está en `main` del ETL. El parche deja una copia en `data/open/bureau_pronostico.json` para que el tablero se vea antes de ese pull.

El daily del ETL corre `models/pronosticar.py` después de exportar seguridad y antes de publicar. Si faltan las librerías, publica solo el mes anterior y lo dice. Si el entrenamiento falla, no borra el JSON anterior.
