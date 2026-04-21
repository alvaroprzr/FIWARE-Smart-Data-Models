# PRD.md — BiciCoruña Smart
## Product Requirements Document
**Versión:** 1.0  
**Fecha:** 2025  
**Asignatura:** Gestión de Datos en Entornos Inteligentes — Práctica 3  
**Escenario:** Gestión de bicicletas compartidas en la ciudad (Escenario 6)  
**Ciudad:** A Coruña, Galicia  

---

## 1. Visión del Producto

**BiciCoruña Smart** es una plataforma inteligente de gestión y uso de bicicletas compartidas en A Coruña. Integra datos en tiempo real del sistema de bicicletas (GBFS), información meteorológica y modelos de movilidad urbana (OSLO) para ofrecer dos capas de valor:

- **Capa ciudadana:** interfaz web responsiva para que cualquier usuario pueda localizar bicis disponibles, planificar rutas y consultar predicciones de disponibilidad mediante un asistente conversacional basado en LLM.
- **Capa analítica:** dashboards operacionales y predictivos con datos históricos, heatmaps de demanda y métricas de impacto ambiental, accesibles también para el ciudadano.

La aplicación está construida sobre los estándares **NGSI-LD**, usando los Smart Data Models **dataModel.GBFS** y **dataModel.OSLO**, y se apoya en los componentes FIWARE: **Orion Context Broker**, **IoT Agent MQTT** y **QuantumLeap**.

---

## 2. Objetivos del Producto

| ID | Objetivo |
|----|----------|
| OBJ-01 | Proporcionar disponibilidad en tiempo real de bicicletas y anclajes en cada estación de A Coruña |
| OBJ-02 | Predecir la disponibilidad futura (30–60 min) usando ML con variables de uso histórico y meteorología |
| OBJ-03 | Facilitar al ciudadano la planificación de rutas ciclistas teniendo en cuenta la topografía de A Coruña |
| OBJ-04 | Ofrecer un asistente IA conversacional que responda consultas sobre el sistema en lenguaje natural |
| OBJ-05 | Proveer dashboards analíticos públicos con patrones de uso, demanda y métricas de sostenibilidad |
| OBJ-06 | Modelar el sistema con NGSI-LD usando entidades GBFS, OSLO, Device y WeatherObserved relacionadas mediante refs |

---

## 3. Usuarios y Roles

### 3.1 Ciudadano / Ciclista
Usuario final que accede desde móvil o navegador web. No requiere autenticación para consultar datos. Su objetivo es localizar bicis, planificar su trayecto y conocer la disponibilidad futura.

### 3.2 Analista / Operador de flota
Usuario con acceso al dashboard analítico completo. Monitoriza el estado de la flota, analiza patrones de uso, detecta desequilibrios entre estaciones y consulta predicciones de redistribución.

### 3.3 Sistema IoT (actor no humano)
Sensores físicos de los anclajes y GPS de las bicicletas que envían datos de estado vía MQTT al IoT Agent. Representados en el modelo de datos mediante la entidad `Device`.

---

## 4. Funcionalidades Principales

| ID | Funcionalidad | Rol | Prioridad |
|----|---------------|-----|-----------|
| F-01 | Mapa interactivo de estaciones con disponibilidad en tiempo real | Ciudadano | Alta |
| F-02 | Detalle de estación: bicis disponibles, anclajes libres, última actualización | Ciudadano | Alta |
| F-03 | Predicción de disponibilidad a 30 y 60 minutos por estación | Ciudadano | Alta |
| F-04 | Asistente IA conversacional (LLM) con acceso a datos en tiempo real | Ciudadano | Alta |
| F-05 | Planificador de ruta entre dos estaciones con perfil de dificultad topográfico | Ciudadano | Media |
| F-06 | Alertas de disponibilidad en estaciones favoritas (push web) | Ciudadano | Media |
| F-07 | Vista 3D de la ciudad con estado de estaciones superpuesto | Ciudadano | Media |
| F-08 | Dashboard de uso histórico: viajes, horas pico, días de la semana | Analista | Alta |
| F-09 | Heatmap de demanda por zonas de A Coruña | Analista | Alta |
| F-10 | Predicción de redistribución: estaciones en riesgo de vaciarse o llenarse | Analista | Alta |
| F-11 | Correlación clima–uso: impacto del viento y la lluvia en la demanda | Analista | Alta |
| F-12 | Panel de impacto ambiental: CO₂ ahorrado, km totales, viajes equivalentes | Ciudadano / Analista | Media |
| F-13 | Interfaz web responsiva adaptada a dispositivos móviles | Ciudadano | Alta |

---

## 5. Historias de Usuario

### Módulo: Mapa y Disponibilidad en Tiempo Real

**HU-01**
> *Como ciudadano, quiero ver en un mapa todas las estaciones de BiciCoruña con su disponibilidad actual, para saber de un vistazo dónde hay bicis disponibles cerca de mí.*

**Criterios de aceptación:**
- El mapa carga en menos de 3 segundos con todas las estaciones visibles.
- Cada marcador muestra un color según disponibilidad: verde (>5 bicis), amarillo (1–5), rojo (0).
- Al hacer clic en un marcador se muestra: nombre de la estación, bicis disponibles, anclajes libres, última actualización.
- Los datos se refrescan automáticamente cada 30 segundos desde Orion CB (NGSI-LD).

---

**HU-02**
> *Como ciudadano, quiero consultar la predicción de disponibilidad de una estación concreta para los próximos 30 y 60 minutos, para planificar mi viaje con antelación.*

**Criterios de aceptación:**
- La predicción se muestra como número estimado de bicis disponibles con un intervalo de confianza.
- El modelo considera: histórico de uso de esa estación, hora del día, día de la semana y condiciones meteorológicas actuales (viento, lluvia).
- Si la predicción indica disponibilidad baja (<2 bicis), se muestra una advertencia visual.
- El modelo se entrena sobre datos históricos almacenados en QuantumLeap / CrateDB.

---

**HU-03**
> *Como ciudadano, quiero consultar en lenguaje natural información sobre el sistema de bicicletas, para obtener respuestas rápidas sin tener que navegar por la interfaz.*

**Criterios de aceptación:**
- El asistente puede responder preguntas como: "¿Dónde hay bicis cerca de la Torre de Hércules?", "¿Cuántas bicis hay ahora en María Pita?", "¿A qué hora suele haber más disponibilidad?".
- El LLM accede en tiempo real a los datos de Orion CB a través del backend FastAPI.
- Las respuestas incluyen nombres reales de estaciones y datos actualizados.
- El asistente indica cuando un dato es una predicción y no un valor en tiempo real.

---

**HU-04**
> *Como ciudadano, quiero ver una ruta ciclista entre dos estaciones con información sobre el desnivel, para elegir la ruta más adecuada a mi condición física.*

**Criterios de aceptación:**
- El usuario selecciona origen y destino en el mapa o por nombre de estación.
- La ruta se traza sobre OSM con perfil de elevación calculado con GeoPandas.
- Se muestra: distancia total, desnivel acumulado, tiempo estimado (10–14 km/h media ciclista).
- Se clasifica la ruta como Fácil / Moderada / Difícil según desnivel acumulado.

---

**HU-05**
> *Como ciudadano, quiero recibir una notificación cuando mi estación favorita tenga bicis disponibles, para no tener que estar revisando la app manualmente.*

**Criterios de aceptación:**
- El usuario puede marcar hasta 3 estaciones como favoritas.
- Las alertas se envían via push web cuando la disponibilidad sube de 0 a ≥1 bicis.
- El sistema usa la suscripción de Orion CB + IoT Agent MQTT para detectar el cambio de estado.
- El usuario puede desactivar las alertas en cualquier momento.

---

**HU-06**
> *Como ciudadano, quiero explorar una visualización 3D de A Coruña con el estado de las estaciones superpuesto, para tener una perspectiva urbana inmersiva del sistema.*

**Criterios de aceptación:**
- La escena 3D renderiza el mapa urbano de A Coruña con altimetría.
- Las estaciones se representan como torres de altura proporcional al número de bicis disponibles.
- Los colores siguen el mismo código que el mapa 2D.
- La escena es interactiva: se puede rotar, hacer zoom y clicar en estaciones.

---

### Módulo: Dashboards Analíticos

**HU-07**
> *Como analista u operador, quiero ver un dashboard con el histórico de uso por estación, hora y día de la semana, para identificar patrones de demanda.*

**Criterios de aceptación:**
- El dashboard se despliega en Grafana conectado a QuantumLeap / CrateDB.
- Permite filtrar por estación, rango de fechas y franja horaria.
- Muestra gráficas de barras (uso por hora), líneas (evolución diaria) y tabla de estaciones más usadas.
- Los datos históricos provienen de las entidades `GBFSStationStatus` almacenadas en QuantumLeap.

---

**HU-08**
> *Como analista, quiero ver un heatmap de demanda por zonas de A Coruña, para identificar áreas con necesidad de más estaciones o bicis.*

**Criterios de aceptación:**
- El heatmap se genera sobre el mapa de Leaflet a partir de datos históricos de viajes (entidad `Trip` de OSLO).
- Se puede filtrar por franja horaria (mañana / tarde / noche) y por día tipo (laborable / fin de semana).
- Las zonas de alta demanda se destacan en rojo; las de baja demanda en azul.

---

**HU-09**
> *Como analista, quiero ver la correlación entre las condiciones meteorológicas y el uso del sistema, para entender el impacto del clima coruñés en la demanda.*

**Criterios de aceptación:**
- Se representa gráficamente la correlación entre `windSpeed`, `precipitation` (de `WeatherObserved`) y el número de viajes iniciados en esa hora.
- El viento es tratado como variable principal dada la orografía costera de A Coruña.
- Se muestra el coeficiente de correlación de Pearson calculado con Pandas/Polars.

---

**HU-10**
> *Como ciudadano o analista, quiero consultar el impacto ambiental acumulado del sistema, para concienciarme sobre los beneficios del transporte sostenible.*

**Criterios de aceptación:**
- Se muestra: CO₂ ahorrado estimado (kg), km totales recorridos y número de viajes completados.
- El cálculo asume un ahorro estándar de 0.21 kg CO₂/km respecto al vehículo privado.
- Los datos se actualizan diariamente desde QuantumLeap.
- La visualización usa ChartJS con contadores animados en la landing page.

---

## 6. Requisitos No Funcionales

| ID | Requisito |
|----|-----------|
| RNF-01 | Toda la comunicación con Orion CB usa **NGSI-LD** (no NGSIv2) |
| RNF-02 | Las relaciones entre entidades se definen con `"type": "Relationship"` y `"object": "urn:ngsi-ld:..."` |
| RNF-03 | La interfaz web es **responsiva** y funcional en pantallas desde 360px de ancho |
| RNF-04 | El tiempo de carga inicial de la vista de mapa es inferior a **3 segundos** |
| RNF-05 | Los datos de estado de estaciones se refrescan con una latencia máxima de **30 segundos** |
| RNF-06 | El modelo ML de predicción tiene un error medio absoluto (MAE) inferior a **2 bicicletas** |
| RNF-07 | La aplicación se despliega completamente con **Docker Compose** (un solo comando) |
| RNF-08 | Todos los datos de prueba son sintéticos pero geográficamente coherentes con A Coruña |

---

## 7. Smart Data Models utilizados

| Modelo | Entidad | Tipo |
|--------|---------|------|
| dataModel.GBFS | `GBFSStation` | Estático |
| dataModel.GBFS | `GBFSStationStatus` | Dinámico (IoT) |
| dataModel.GBFS | `GBFSFreeBikeStatus` | Dinámico (IoT) |
| dataModel.GBFS | `GBFSSystemInformation` | Estático |
| dataModel.GBFS | `GBFSGeofencingZone` | Estático |
| dataModel.OSLO | `MobilityStation` | Estático |
| dataModel.OSLO | `Trip` | Dinámico (histórico) |
| Cross-sector | `Device` | Estático / semi-dinámico |
| dataModel.Weather | `WeatherObserved` | Dinámico (externo) |

---

## 8. Tecnologías

| Capa | Tecnología | Uso |
|------|-----------|-----|
| Context Broker | Orion CB (NGSI-LD) | Estado actual de todas las entidades |
| IoT | IoT Agent MQTT (JSON) | Ingesta de datos de sensores de anclajes |
| Histórico | QuantumLeap + CrateDB | Series temporales para ML y Grafana |
| Backend | FastAPI (Python) | API REST, orquestación, ML serving |
| Frontend | HTML + JS + Tailwind CSS | Interfaz responsiva web |
| Mapas | Leaflet + OpenStreetMap | Mapa 2D interactivo y heatmap |
| 3D | ThreeJS | Vista inmersiva de la ciudad |
| Gráficos | ChartJS | Visualizaciones en frontend |
| Dashboards | Grafana | Dashboards operacionales históricos |
| ML | scikit-learn / statsmodels | Modelo predictivo de demanda |
| Análisis | Pandas, GeoPandas, Polars | Procesamiento de datos y rutas |
| LLM | Claude API (Anthropic) | Asistente conversacional |
| Despliegue | Docker Compose | Orquestación de todos los servicios |

---

## 9. Fuera de Alcance (v1.0)

- Sistema de pago o reserva de bicicletas.
- Autenticación de usuarios (login / perfil personal).
- Integración con sistemas de bicicletas reales de A Coruña (los datos son simulados).
- App nativa iOS / Android (solo web responsiva).
- Mantenimiento predictivo de bicicletas (posible v2.0).

---

*Documento generado como parte de la Práctica 3 — Gestión de Datos en Entornos Inteligentes, Universidade da Coruña.*
