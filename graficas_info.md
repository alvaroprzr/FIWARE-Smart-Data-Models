# Información de Gráficas (Grafana)

Este documento detalla el propósito, la métrica y las consultas subyacentes de cada uno de los paneles (gráficas) mostrados en el dashboard de Grafana de **BiciCoruña Smart**. 

El dashboard lee sus datos directamente del histórico almacenado en **CrateDB**, el cual recopila continuamente eventos a través del broker de contexto Orion-LD y el IoT Agent. Todas las gráficas son sensibles al selector temporal (por defecto: _Últimas 24 horas_) y al filtro de estación (`$station`).

---

## 1. Disponibilidad media por estación (Gráfico de Barras horizontal)
* **Objetivo:** Comparar, de forma agregada, la disponibilidad media de bicicletas y plazas libres en **todas las estaciones** de la red durante el período seleccionado. Permite detectar qué estaciones suelen estar más vacías y cuáles más llenas.
* **Consulta SQL:**
  `SELECT station_id, AVG(num_bikes_available) as media_bicis, AVG(num_docks_available) as media_plazas FROM etstation_status WHERE $__timeFilter(time) GROUP BY station_id ORDER BY media_bicis DESC`
* **Comportamiento:**
  Muestra una barra doble por estación (verde: bicis disponibles, azul: plazas libres). No filtra por `$station`; muestra siempre todas las estaciones para facilitar la comparación.

## 2. Viajes por hora del día (Gráfico de Barras)
* **Objetivo:** Identificar los "picos de uso" a lo largo de un día típico, mostrando cuántos alquileres/viajes se inician en cada franja horaria.
* **Consulta SQL:** 
  Lee la tabla `trips`. Extrae exclusivamente la "hora" (00 a 23) de la fecha de inicio (`started_at`) de cada viaje y cuenta la suma total de viajes en cada hora.
* **Comportamiento:** 
  Independientemente del día exacto en el que ocurra el viaje, lo agrupa por "hora del día", permitiendo ver a qué hora la gente coge más bicicletas (ej. picos a las 08:00h y a las 18:00h).

## 3. Bicicletas disponibles por estación y hora (Gráfico de Líneas con agregación)
* **Objetivo:** Ofrecer una visión comparativa y agregada de la disponibilidad promedio de bicicletas **para todas las estaciones** de la red.
* **Consulta SQL:** 
  Lee la tabla `etstation_status`. Utiliza `DATE_TRUNC('hour', ...)` para empaquetar los reportes de las estaciones en bloques horarios de 1 hora de duración. Calcula la media (`AVG`) de las bicis disponibles durante esa hora.
* **Comportamiento:** 
  Genera múltiples líneas (una por cada estación). Es ideal para detectar qué estaciones se vacían constantemente y cuáles permanecen llenas durante un rango de tiempo amplio.

## 4. CO₂ Ahorrado Total (Métrica de Texto / Gauge)
* **Objetivo:** Medir el impacto ecológico positivo del uso del servicio de bicicletas respecto a un coche de combustión equivalente.
* **Consulta SQL:** 
  `SELECT ROUND((SUM(distance_meters)/1000.0 * 0.21) * 10) / 10.0 as co2_kg FROM trips`
* **Cálculo:**
  1. Suma la distancia en metros de todos los viajes.
  2. Divide entre 1000 para obtener Kilómetros.
  3. Multiplica por un factor de emisiones conservador de **0.21 kg de CO₂ por kilómetro** (basado en medias europeas de emisiones de coches de combustión interna).
  4. Redondea a un decimal para mayor claridad.

## 5. Correlación Viento y Precipitación vs Viajes (Doble Eje Y)
* **Objetivo:** Descubrir si los factores meteorológicos (velocidad del viento y precipitación) afectan a la cantidad de personas que se animan a alquilar una bici.
* **Consulta SQL (Combinada, 3 series):**
  1. Extrae los viajes agrupados por hora de la tabla `trips`.
  2. Extrae la velocidad del viento de la tabla `etweatherobserved`.
  3. Extrae la precipitación de la tabla `etweatherobserved`.
* **Comportamiento:**
  Muestra tres series superpuestas: conteo de viajes (eje izquierdo), velocidad del viento (eje derecho, m/s) y precipitación (eje derecho, mm). Permite comprobar visualmente si los picos de viento o lluvia coinciden con caídas en el uso del sistema.

## 6. Estaciones más usadas — Top 10 (Tabla)
* **Objetivo:** Identificar las estaciones con mayor volumen de salidas y la distancia media recorrida desde ellas durante el período seleccionado.
* **Consulta SQL:**
  `SELECT start_station_id as estacion, COUNT(*) as viajes, ROUND(AVG(distance_meters) / 1000.0) as km_medio FROM trips WHERE $__timeFilter(started_at) GROUP BY start_station_id ORDER BY viajes DESC LIMIT 10`
* **Comportamiento:**
  Tabla ordenada descendentemente por número de viajes. Muestra el ID de la estación de origen, el total de viajes iniciados y la distancia media en kilómetros (redondeada al km más cercano).

## 7. Rutas más frecuentes — Top 10 origen → destino (Tabla)
* **Objetivo:** Identificar los pares origen–destino con más viajes realizados, útiles para detectar corredores de movilidad recurrentes (commute, ocio, conexión con campus, etc.).
* **Consulta SQL:**
  `SELECT start_station_id AS origen, end_station_id AS destino, COUNT(*) AS viajes, ROUND(AVG(distance_meters) / 1000.0, 2) AS km_medio FROM trips WHERE $__timeFilter(started_at) GROUP BY start_station_id, end_station_id ORDER BY viajes DESC LIMIT 10`
* **Comportamiento:**
  Tabla ordenada descendentemente por número de viajes. Muestra el ID de la estación de origen, el ID de la estación de destino, el número total de viajes en ese trayecto y la distancia media (km).

> **Nota:** El cálculo cuantitativo de correlación de Pearson (r) entre clima y demanda se sirve vía el endpoint backend `GET /api/weather/correlation` (no representado como panel Grafana en la versión actual del dashboard).
