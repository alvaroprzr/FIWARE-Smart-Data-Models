# PRD.md — Smart Mobility Hub · BiciCoruña Smart
## Product Requirements Document
**Versión:** 2.0 (Final)
**Fecha:** 2025
**Asignatura:** Gestión de Datos en Entornos Inteligentes — Práctica 3
**Escenario:** Gestión de bicicletas compartidas en la ciudad (Escenario 6)
**Ciudad piloto:** A Coruña, Galicia
**Stack Grafana local:** smartmobilityhub

---

## 1. Visión del Producto

**Smart Mobility Hub** es una plataforma inteligente de gestión y análisis de sistemas de bicicletas compartidas, desplegada inicialmente sobre el escenario real de **BiciCoruña** en A Coruña.

A diferencia de soluciones de ciudad única, la plataforma emplea una **arquitectura multi-región** basada en estándares internacionales (NGSI-LD, GBFS, OSLO), lo que permite incorporar nuevas ciudades de forma modular sin rediseño de la infraestructura. A Coruña actúa como ciudad piloto y referencia de validación, aprovechando su orografía costera y el efecto climático del viento atlántico como variables diferenciadoras en los modelos predictivos.

La plataforma ofrece dos capas de valor complementarias:

- **Capa ciudadana:** interfaz web responsiva con mapa interactivo de disponibilidad en tiempo real, planificador de rutas con perfil topográfico, predicciones de demanda y un asistente conversacional IA con acceso al contexto vivo de la ciudad.
- **Capa analítica:** entorno de observabilidad y análisis histórico (Grafana local) con dashboards parametrizados por ciudad y estación, heatmaps de demanda, correlación clima–uso y métricas de sostenibilidad.

La infraestructura se apoya en los componentes FIWARE obligatorios — **Orion Context Broker (NGSI-LD)**, **IoT Agent MQTT** y **QuantumLeap + CrateDB** — y se orquesta mediante **Docker Compose** en un único comando.

---

## 2. Objetivos del Producto

| ID | Objetivo |
|----|----------|
| OBJ-01 | Proporcionar disponibilidad en tiempo real de bicicletas y anclajes por estación, en cualquier ciudad configurada |
| OBJ-02 | Predecir la disponibilidad futura (30–60 min) mediante ML usando histórico de uso y variables meteorológicas (especialmente viento) |
| OBJ-03 | Facilitar la planificación de rutas ciclistas con perfil de dificultad topográfico adaptado a la orografía de cada ciudad |
| OBJ-04 | Ofrecer un asistente IA conversacional con acceso en tiempo real al contexto de Orion CB |
| OBJ-05 | Proveer dashboards analíticos en Grafana local parametrizados por ciudad y estación |
| OBJ-06 | Implementar una arquitectura multi-región seleccionable desde la interfaz, escalable a nuevas ciudades |
| OBJ-07 | Modelar el sistema con NGSI-LD usando entidades GBFS, OSLO, Device y WeatherObserved relacionadas mediante `refs` |
| OBJ-08 | Calcular dinámicamente métricas de sostenibilidad: CO₂ ahorrado, km recorridos, viajes equivalentes |

---

## 3. Usuarios y Roles

### 3.1 Ciudadano / Ciclista
Usuario final que accede desde móvil o navegador web. No requiere autenticación. Selecciona su ciudad desde la interfaz y puede localizar bicis, planificar rutas, consultar predicciones y usar el asistente conversacional.

### 3.2 Analista / Operador de Flota
Usuario con acceso al dashboard analítico completo en Grafana local. Monitoriza el estado de la flota, detecta desequilibrios entre estaciones y analiza patrones de uso histórico. Puede filtrar por ciudad, estación y rango temporal.

### 3.3 Sistema IoT (actor no humano)
Sensores físicos de los anclajes y GPS de las bicicletas que envían datos de estado vía MQTT al IoT Agent. Representados en el modelo de datos mediante la entidad `Device` (cross-sector). Sus lecturas se mapean a las entidades de negocio `GBFSStationStatus` y `GBFSFreeBikeStatus`.

---

## 4. Funcionalidades Principales

| ID | Funcionalidad | Rol | Prioridad |
|----|---------------|-----|-----------|
| F-01 | Mapa interactivo multi-ciudad con disponibilidad en tiempo real | Ciudadano | Alta |
| F-02 | Selector de ciudad/región en la interfaz con cambio dinámico de contexto | Ciudadano | Alta |
| F-03 | Detalle de estación: bicis disponibles, anclajes libres, última actualización | Ciudadano | Alta |
| F-04 | Predicción de disponibilidad a 30 y 60 minutos por estación | Ciudadano | Alta |
| F-05 | Asistente IA conversacional con acceso en tiempo real a Orion CB | Ciudadano | Alta |
| F-06 | Planificador de ruta entre estaciones con perfil de dificultad topográfico | Ciudadano | Media |
| F-07 | Alertas de disponibilidad en estaciones favoritas (push web) | Ciudadano | Media |
| F-08 | Vista 3D de la ciudad con estado de estaciones superpuesto | Ciudadano | Media |
| F-09 | Dashboard histórico parametrizado por ciudad y estación (Grafana local) | Analista | Alta |
| F-10 | Heatmap de demanda por zonas de la ciudad | Analista | Alta |
| F-11 | Predicción de redistribución: estaciones en riesgo de vaciarse o llenarse | Analista | Alta |
| F-12 | Correlación clima–uso: impacto de viento y lluvia en la demanda | Analista | Alta |
| F-13 | Panel de impacto ambiental: CO₂ ahorrado, km totales, viajes | Ciudadano / Analista | Media |
| F-14 | Interfaz web responsiva adaptada a dispositivos móviles (desde 360px) | Ciudadano | Alta |
| F-15 | Paneles Grafana embebidos vía iFrame en el frontend ciudadano | Ciudadano / Analista | Media |

---

## 5. Historias de Usuario

### Módulo: Mapa y Disponibilidad en Tiempo Real

**HU-01**
> *Como ciudadano, quiero ver en un mapa todas las estaciones de la ciudad seleccionada con su disponibilidad actual, para saber de un vistazo dónde hay bicis disponibles cerca de mí.*

**Criterios de aceptación:**
- El mapa carga en menos de 3 segundos con todas las estaciones de la ciudad activa.
- El selector de ciudad cambia el contexto completo del mapa sin recargar la página.
- Cada marcador muestra un color según disponibilidad: verde (>5 bicis), amarillo (1–5), rojo (0).
- Al hacer clic en un marcador se muestra: nombre de estación, bicis disponibles, anclajes libres, última actualización.
- Los datos se refrescan automáticamente cada 30 segundos desde Orion CB (NGSI-LD).

---

**HU-02**
> *Como ciudadano, quiero seleccionar la ciudad o región que me interesa desde la interfaz, para consultar el sistema de bicicletas de esa área concreta.*

**Criterios de aceptación:**
- La interfaz presenta un selector de ciudad en la barra de navegación principal.
- El cambio de ciudad actualiza el mapa, los datos de estaciones y el contexto del asistente IA.
- A Coruña aparece seleccionada por defecto como ciudad piloto.
- La arquitectura backend soporta filtrado por ciudad mediante el atributo `addressLocality` de las entidades NGSI-LD.

---

**HU-03**
> *Como ciudadano, quiero consultar la predicción de disponibilidad de una estación concreta para los próximos 30 y 60 minutos, para planificar mi viaje con antelación.*

**Criterios de aceptación:**
- La predicción se muestra como número estimado de bicis disponibles con un intervalo de confianza.
- El modelo considera: histórico de uso, hora del día, día de la semana, `windSpeed` y `precipitation` de `WeatherObserved`. El viento es la variable climática principal para A Coruña.
- Si la predicción indica disponibilidad baja (<2 bicis), se muestra una advertencia visual.
- El modelo se entrena sobre datos históricos almacenados en QuantumLeap / CrateDB mediante Pandas + scikit-learn (RandomForest), con horizontes de 30 y 60 minutos.
- Si los modelos entrenados no están disponibles, el backend responde con un fallback de media histórica por estación y hora para mantener continuidad del servicio.

---

**HU-04**
> *Como ciudadano, quiero consultar en lenguaje natural el estado del sistema, para obtener respuestas rápidas sin navegar por menús.*

**Criterios de aceptación:**
- El asistente responde preguntas como: "¿Dónde hay bicis cerca de la Torre de Hércules?", "¿Cuántas bicis hay en María Pita?", "¿A qué hora hay más disponibilidad?".
- El backend (FastAPI) usa _function calling_ para consultar Orion CB antes de formular la respuesta, inyectando el contexto real en el prompt del LLM.
- El LLM principal es **Gemma** ejecutado localmente vía **LM Studio** (privacidad, sin dependencia externa) mediante endpoint compatible con la API de OpenAI.
- El asistente responde en menos de 5 segundos en hardware local estándar.
- El asistente indica explícitamente cuando un dato es una predicción y no un valor en tiempo real.
- Las respuestas incluyen nombres reales de estaciones y datos actualizados de la ciudad seleccionada.

---

**HU-05**
> *Como ciudadano, quiero ver una ruta ciclista entre dos estaciones con información sobre el desnivel, para elegir la ruta más adecuada a mi condición física.*

**Criterios de aceptación:**
- El usuario selecciona origen y destino en el mapa o por nombre de estación.
- La ruta se traza sobre OSM con perfil de elevación calculado con GeoPandas.
- Se muestra: distancia total, desnivel acumulado y tiempo estimado (10–14 km/h media ciclista).
- La ruta se clasifica como Fácil / Moderada / Difícil según el desnivel acumulado.

---

**HU-06**
> *Como ciudadano, quiero recibir una notificación cuando mi estación favorita tenga bicis disponibles, para no tener que revisar la app manualmente.*

**Criterios de aceptación:**
- El usuario puede marcar hasta 3 estaciones como favoritas.
- Las alertas se envían vía push web cuando la disponibilidad sube de 0 a ≥1 bicis.
- El sistema usa suscripciones de Orion CB + IoT Agent MQTT para detectar el cambio de estado.
- El usuario puede desactivar las alertas en cualquier momento.

---

**HU-07**
> *Como ciudadano, quiero explorar una visualización 3D de la ciudad con el estado de las estaciones superpuesto, para tener una perspectiva urbana inmersiva del sistema.*

**Criterios de aceptación:**
- La escena 3D renderiza el mapa urbano con altimetría real usando ThreeJS.
- Las estaciones se representan como torres de altura proporcional al número de bicis disponibles.
- Los colores siguen el mismo código que el mapa 2D (verde / amarillo / rojo).
- La escena es interactiva: permite rotar, hacer zoom y clicar en estaciones para ver su detalle.

---

### Módulo: Dashboards Analíticos

**HU-08**
> *Como analista, quiero visualizar el histórico de uso parametrizado por ciudad y estación en Grafana local, para identificar patrones de demanda a lo largo del tiempo.*

**Criterios de aceptación:**
- Los dashboards se despliegan en la instancia local de Grafana (stack lógico `smartmobilityhub`), conectada a CrateDB mediante SQL estándar.
- Los dashboards están parametrizados con variables de plantilla (`$city`, `$station`) para soportar múltiples regiones sin duplicar paneles.
- Permite filtrar por rango de fechas y franja horaria.
- Muestra: gráficas de barras (uso por hora), líneas (evolución diaria) y tabla de estaciones más usadas.
- Los datos provienen de las entidades `GBFSStationStatus` y `Trip` almacenadas en QuantumLeap.

---

**HU-09**
> *Como analista, quiero ver un heatmap de demanda por zonas de la ciudad, para identificar áreas con necesidad de más estaciones o redistribución de bicis.*

**Criterios de aceptación:**
- El heatmap se genera sobre el mapa Leaflet a partir de datos históricos de la entidad `Trip` (OSLO).
- Se puede filtrar por franja horaria (mañana / tarde / noche) y tipo de día (laborable / fin de semana).
- Las zonas de alta demanda se destacan en rojo; las de baja demanda en azul.

---

**HU-10**
> *Como analista, quiero ver la correlación entre las condiciones meteorológicas y el uso del sistema, para entender el impacto del clima en la demanda ciclista.*

**Criterios de aceptación:**
- Se representa gráficamente la correlación entre `windSpeed`, `precipitation` (de `WeatherObserved`) y el número de viajes iniciados por hora.
- El viento se trata como variable climática principal dada la orografía costera de A Coruña.
- Se muestra el coeficiente de correlación de Pearson, calculado con Pandas/Polars.

---

**HU-11**
> *Como ciudadano o analista, quiero consultar el impacto ambiental acumulado del sistema, para concienciarme sobre los beneficios del transporte sostenible.*

**Criterios de aceptación:**
- Se muestra: CO₂ ahorrado estimado (kg), km totales recorridos y número de viajes completados.
- El cálculo asume un ahorro de 0,21 kg CO₂/km respecto al vehículo privado de combustión.
- Los datos se actualizan diariamente desde QuantumLeap.
- La visualización usa ChartJS con contadores animados en la landing page.
- Los paneles de Grafana con estas métricas se embeben en el frontend vía iFrame.

---

## 6. Requisitos No Funcionales

| ID | Requisito | Detalle |
|----|-----------|---------|
| RNF-01 | NGSI-LD nativo | Toda la comunicación con Orion CB usa NGSI-LD con `@context`. Sin NGSIv2. |
| RNF-02 | Relaciones NGSI-LD | Las `refs` entre entidades se definen con `"type": "Relationship"` y `"object": "urn:ngsi-ld:..."` |
| RNF-03 | Responsividad | La interfaz web es funcional en pantallas desde 360px de ancho |
| RNF-04 | Rendimiento de carga | El mapa inicial carga en menos de 3 segundos |
| RNF-05 | Latencia IoT | Los datos de estaciones se refrescan con una latencia máxima de 30 segundos |
| RNF-06 | Calidad ML | El modelo predictivo tiene un error medio absoluto (MAE) inferior a 2 bicicletas |
| RNF-07 | Despliegue único | La aplicación completa se levanta con `docker compose up` (un solo comando), incluyendo provisionamiento de Grafana y entrenamiento de modelos |
| RNF-08 | Datos coherentes | Los datos de prueba son sintéticos pero geográficamente coherentes con A Coruña |
| RNF-09 | Seguridad | Gestión de acceso a CrateDB y Orion CB mediante API Keys; endpoints internos no expuestos públicamente |
| RNF-10 | Inferencia local | El asistente IA responde en menos de 5 segundos en hardware local con LM Studio |

---

## 7. Smart Data Models Utilizados

| Modelo | Entidad | Tipo | Descripción |
|--------|---------|------|-------------|
| dataModel.GBFS | `GBFSStation` | Estático | Información fija de la estación: nombre, ubicación, capacidad |
| dataModel.GBFS | `GBFSStationStatus` | **Dinámico (IoT)** | Estado en tiempo real: bicis disponibles, anclajes libres |
| dataModel.GBFS | `GBFSFreeBikeStatus` | **Dinámico (IoT)** | Estado de bicis libres o flotantes |
| dataModel.GBFS | `GBFSSystemInformation` | Estático | Información global del sistema por ciudad |
| dataModel.GBFS | `GBFSGeofencingZone` | Estático | Zonas permitidas y restringidas de circulación |
| dataModel.OSLO | `MobilityStation` | Estático | Complementa GBFSStation con atributos de movilidad intermodal |
| dataModel.OSLO | `Trip` | **Dinámico (histórico)** | Viaje realizado: origen, destino, duración, distancia |
| Cross-sector | `Device` | Semi-estático | Sensor de anclaje o GPS de bicicleta. Enlaza capa firmware con entidades de negocio |
| dataModel.Weather | `WeatherObserved` | **Dinámico (externo)** | Condiciones meteorológicas: viento, lluvia, temperatura |

### Relaciones entre entidades (NGSI-LD refs)

```
GBFSStationStatus  ──refStation──────► GBFSStation
GBFSFreeBikeStatus ──refStation──────► GBFSStation
MobilityStation    ──refGBFSStation──► GBFSStation
Trip               ──refVehicle──────► Device (bici GPS)
Trip               ──refOrigin────────► GBFSStation
Trip               ──refDestination──► GBFSStation
GBFSStation        ──refWeather──────► WeatherObserved
Device             ──refStation──────► GBFSStation
```

---

## 8. Tecnologías

| Capa | Tecnología | Uso |
|------|-----------|-----|
| Context Broker | Orion-LD (NGSI-LD) | Gestión de contexto y estado actual de todas las entidades |
| IoT | IoT Agent MQTT (JSON) | Traducción de mensajes MQTT de sensores a entidades NGSI-LD |
| Histórico | QuantumLeap + CrateDB | Series temporales para ML, Grafana y análisis con Pandas |
| Dashboards | Grafana local (`smartmobilityhub`) | Visualización analítica histórica multi-ciudad parametrizada |
| Backend | FastAPI (Python) | API REST, orquestación, function calling para LLM, ML serving |
| Asistente IA | Gemma vía LM Studio (local, API compatible OpenAI) | Asistente conversacional con contexto vivo de Orion CB |
| Frontend | HTML + JS + Tailwind CSS | Interfaz web responsiva con selector de ciudad |
| Mapas 2D | Leaflet + OpenStreetMap | Mapa interactivo, heatmap y trazado de rutas |
| Mapas 3D | ThreeJS | Vista inmersiva urbana con altimetría |
| Gráficos | ChartJS | Visualizaciones inline en el frontend |
| Análisis | Pandas, GeoPandas, Polars | Procesamiento de datos, rutas y correlaciones |
| ML | scikit-learn / statsmodels | Modelos predictivos de demanda por estación |
| Despliegue | Docker Compose | Orquestación completa de todos los servicios |

---

## 9. Arquitectura de Datos — Estático vs. Dinámico

| Atributo | Entidad | Tipo | Canal de actualización |
|----------|---------|------|------------------------|
| `location`, `address`, `capacity` | `GBFSStation` | Estático | Carga inicial / script de provisioning |
| `numBikesAvailable`, `numDocksAvailable`, `lastReported` | `GBFSStationStatus` | **Dinámico** | IoT Agent MQTT → Orion CB |
| `bike_id`, `is_reserved`, `lat`, `lon` | `GBFSFreeBikeStatus` | **Dinámico** | IoT Agent MQTT → Orion CB |
| `startStation`, `endStation`, `duration`, `distance` | `Trip` | **Dinámico** | Backend FastAPI → Orion CB |
| `windSpeed`, `precipitation`, `temperature` | `WeatherObserved` | **Dinámico** | Servicio externo / simulador |
| `deviceState`, `batteryLevel` | `Device` | Semi-dinámico | IoT Agent MQTT → Orion CB |
| `operatorName`, `timezone`, `feedContactEmail` | `GBFSSystemInformation` | Estático | Configuración por ciudad |

---

## 10. Fuera de Alcance (v1.0)

- Sistema de pago o reserva de bicicletas.
- Autenticación de usuarios (login / perfil personal persistente).
- Integración con datos reales de operadores de bicicletas (los datos son sintéticos y geográficamente coherentes).
- App nativa iOS / Android (solo interfaz web responsiva).
- Mantenimiento predictivo de bicicletas (roadmap v2.0).
- Soporte de más de 3 ciudades simultáneas en la versión MVP.

---

*Documento generado como parte de la Práctica 3 — Gestión de Datos en Entornos Inteligentes, Universidade da Coruña.*
