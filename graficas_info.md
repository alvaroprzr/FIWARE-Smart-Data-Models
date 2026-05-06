# Información de Gráficas (Grafana)

Este documento detalla el propósito, la métrica y las consultas subyacentes de cada uno de los paneles (gráficas) mostrados en el dashboard de Grafana de **BiciCoruña Smart**. 

El dashboard lee sus datos directamente del histórico almacenado en **CrateDB**, el cual recopila continuamente eventos a través del broker de contexto Orion-LD y el IoT Agent. Todas las gráficas son sensibles al selector temporal (por defecto: _Últimas 24 horas_) y al filtro de estación (`$station`).

---

## 1. Disponibilidad por estación (Gráfico de Líneas)
* **Objetivo:** Mostrar la evolución a lo largo del tiempo del número de bicicletas y anclajes disponibles para la **estación seleccionada** en el menú superior.
* **Consulta SQL:** 
  Lee la tabla `etstation_status` filtrando por el `station_id` específico.
* **Comportamiento:** 
  Responde al cambio en el menú desplegable. Muestra una línea temporal exacta (sin agregaciones) con cada reporte que ha enviado la estación al sistema.

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

## 5. Correlación Viento vs Viajes (Doble Eje Y)
* **Objetivo:** Descubrir si el factor meteorológico (concretamente, la velocidad del viento) afecta a la cantidad de personas que se animan a alquilar una bici.
* **Consulta SQL (Combinada):**
  1. Extrae los viajes agrupados por hora de la tabla `trips`.
  2. Extrae la velocidad del viento reportada en la tabla meteorológica (`etweatherobserved`).
* **Comportamiento:** 
  Muestra dos ejes superpuestos en la gráfica. En la parte izquierda el conteo de viajes, y en la derecha la velocidad del viento en Km/h o m/s. Permite a los administradores comprobar visualmente si los picos de viento coinciden con caídas en el uso del sistema de alquiler.
