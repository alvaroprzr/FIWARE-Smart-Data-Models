# APPLICATION.md — Smart Mobility Hub

**Escenario:** Gestión inteligente de sistemas de bicicletas compartidas multi-ciudad  
**Ciudad piloto:** A Coruña, Galicia  
**Versión del documento:** 1.0

---

## 1. Objetivo

**Smart Mobility Hub** es una plataforma inteligente de gestión, análisis y predicción de sistemas de bicicletas compartidas, diseñada con una arquitectura **multi-región agnóstica a ciudad** basada en estándares de datos abiertos (NGSI-LD, GBFS, OSLO). A Coruña actúa como ciudad piloto de validación.

A diferencia de soluciones propietarias de ciudad única, la plataforma emplea una estrategia de **interoperabilidad estándar** que permite incorporar nuevas ciudades de forma modular sin rediseño de infraestructura. El sistema ofrece dos capas complementarias: una **capa ciudadana** con mapa interactivo de disponibilidad en tiempo real, predicciones de demanda y asistente conversacional con acceso al contexto vivo de Orion Context Broker; y una **capa analítica** en Grafana Cloud con dashboards parametrizados, heatmaps de demanda y correlación clima–uso.

La orografía costera de A Coruña y el efecto del viento atlántico se modelan como variables diferenciadoras en los análisis predictivos. El despliegue completo se orquesta mediante **Docker Compose en un único comando**, integrando componentes FIWARE obligatorios (Orion-LD, IoT Agent MQTT, QuantumLeap, CrateDB) con un backend FastAPI, frontend responsivo y LLM local (Gemma vía LM Studio).

Los datos de prueba utilizados son **sintéticos pero geográficamente coherentes con A Coruña**, asegurando validez en análisis de patrones y modelos predictivos.

---

## 2. Estado del Arte

**Sistemas existentes** como Bicing (Barcelona), BiciMad (Madrid), Vélib' (París), Lime y Bird operan con arquitecturas **propietarias y cerradas**, donde cada ciudad implementa su propio stack tecnológico, modelos de datos y API, dificultando la transferencia de soluciones o análisis comparativos entre regiones. Aunque estas plataformas ofrecen funcionalidad básica (mapa, disponibilidad, reserva), adolecen de:

- **Fragmentación de datos:** Cada sistema define sus propios esquemas; no hay estándar compartido para interoperabilidad entre ciudades.
- **Escalabilidad limitada:** Agregar una nueva ciudad requiere rediseño integral.
- **Opacidad analítica:** Acceso restringido a datos históricos para ML y análisis de movilidad sostenible.

**Smart Mobility Hub diferencia su enfoque** mediante:

1. **NGSI-LD nativo:** Usa el estándar FIWARE de contexto inteligente como contrato de datos. Todas las entidades (estaciones, bicicletas, observaciones meteorológicas) se modelan como objetos JSON-LD con relaciones explícitas (`Relationship`), permitiendo consultas estructuradas y evolución sin fragmentación.

2. **Interoperabilidad mediante GBFS/FIWARE:** La especificación GBFS (General Bikeshare Feed Specification) se materializa como entidades NGSI-LD (`GBFSStation`, `GBFSStationStatus`, `GBFSFreeBikeStatus`), transformando un feed orientado a consumo en datos semánticos operables e históricos.

3. **Movilidad intermodal (OSLO):** Integra el perfil OSLO (estándar europeo) para modelar viajes (`Trip`) y estaciones multimodales (`MobilityStation`), facilitando futuros análisis de cambio modal.

4. **Machine Learning y predicción local:** Acumula series temporales en QuantumLeap/CrateDB, entrena modelos de demanda incorporando variables meteorológicas (viento, precipitación), y sirve predicciones a 30–60 minutos sin dependencia de APIs externas.

5. **Asistencia conversacional con contexto vivo:** Un LLM local (Gemma) ejecutado en LM Studio realiza **function calling** contra Orion-LD, respondiendo preguntas en lenguaje natural con datos actualizados de la ciudad seleccionada, sin exposición de datos externos.

Esta combinación (NGSI-LD + GBFS + OSLO + ML local + LLM local) constituye un modelo radicalmente diferente: datos abiertos, arquitectura escalable multi-región y análisis autónomo.

---

## 3. Funcionalidades Principales

La plataforma agrupa 15 funcionalidades en tres perfiles:

**Para el Ciudadano (Usuario Final):**
- Mapa interactivo multi-ciudad (F-01) con selector dinámico de región (F-02)
- Detalle de estación: bicis disponibles, anclajes libres, última actualización (F-03)
- Predicción de disponibilidad a 30 y 60 minutos por estación (F-04)
- Asistente IA conversacional con acceso en tiempo real a Orion (F-05)
- Planificador de ruta con perfil de dificultad topográfico (F-06)
- Alertas push web en estaciones favoritas (F-07)
- Vista 3D inmersiva de la ciudad con estado de estaciones superpuesto (F-08)
- Panel de impacto ambiental: CO₂ ahorrado, km totales, viajes equivalentes (F-13)
- Interfaz responsiva para dispositivos móviles desde 360px (F-14)

**Para el Analista / Operador:**
- Dashboard histórico parametrizado por ciudad y estación en Grafana Cloud (F-09)
- Heatmap de demanda por zonas de la ciudad (F-10)
- Predicción de redistribución: estaciones en riesgo de vaciarse o llenarse (F-11)
- Correlación clima–uso: impacto de viento y lluvia en demanda (F-12)
- Paneles Grafana embebidos en el frontend ciudadano vía iFrame (F-15)

---

## 4. Funcionalidades Detalladas

**Módulo 1: Mapa y Disponibilidad en Tiempo Real**

El mapa carga en menos de 3 segundos con todas las estaciones de la ciudad activa. Cada marcador se codifica por color según disponibilidad: verde (>5 bicis), amarillo (1–5), rojo (0). Al clic se muestra nombre de estación, bicis disponibles, anclajes libres y última actualización. El selector de ciudad en la barra de navegación cambia el contexto completo sin recargar página. Los datos se refrescan automáticamente cada 30 segundos desde Orion-LD.

El planificador de rutas permite seleccionar origen y destino en el mapa o por nombre de estación. Se calcula el perfil de elevación usando GeoPandas sobre altimetría OSM, mostrando distancia total, desnivel acumulado y tiempo estimado (10–14 km/h media ciclista). La ruta se clasifica como Fácil/Moderada/Difícil según desnivel.

Las predicciones de disponibilidad integran histórico de uso (QuantumLeap), hora del día, día de la semana y variables meteorológicas de `WeatherObserved` (especialmente `windSpeed` para A Coruña). El modelo se entrena con scikit-learn sobre datos históricos en CrateDB, alcanzando error medio absoluto (MAE) inferior a 2 bicicletas.

**Módulo 2: Dashboards Analíticos y Sostenibilidad**

Los dashboards Grafana se despliegan en el stack `smartmobilityhub` de Grafana Cloud, conectados a CrateDB mediante SQL. Están parametrizados con variables de plantilla (`$city`, `$station`) para soportar múltiples regiones sin duplicación de paneles. Permiten filtrar por rango de fechas, franja horaria, y mostran gráficas de barras (uso por hora), líneas (evolución diaria) y tablas de estaciones más usadas.

El heatmap de demanda se genera sobre Leaflet a partir de datos históricos de la entidad `Trip` (OSLO), permitiendo filtro por franja horaria (mañana/tarde/noche) y tipo de día (laborable/fin de semana). La correlación clima–uso representa gráficamente la relación entre `windSpeed`, `precipitation` y número de viajes iniciados por hora, mostrando coeficiente de Pearson.

El panel de impacto ambiental calcula CO₂ ahorrado (0,21 kg/km respecto a vehículo privado), km totales recorridos y número de viajes completados. Los datos se actualizan diariamente desde QuantumLeap y la visualización usa ChartJS con contadores animados.

---

## 5. Diagrama de Arquitectura

```mermaid
flowchart LR
  subgraph IoT[Flujo IoT]
    S1["Sensor de anclaje MQTT\n/bicicoruna/{stationId}/attrs\nJSON"]
    MQ(["Mosquitto\nMQTT Broker:1883"])
    IA["IoT Agent MQTT JSON\nHTTP 4041 / MQTT 7896"]
    ORI["Orion-LD\nNGSI-LD 1026"]
    S1 -- MQTT/JSON --> MQ
    MQ -- MQTT topic subscription --> IA
    IA -- HTTP PATCH NGSI-LD --> ORI
  end

  subgraph Analytics[Flujo analitico e historico]
    SUB["Subscription station_status\nwatchedAttributes"]
    QL["QuantumLeap\n/v2/notify 8668"]
    CR(["CrateDB\n4200/5432"])
    GRA["Grafana\n3000"]
    ORI -- notify HTTP JSON --> QL
    QL -- INSERT timeseries --> CR
    GRA -- SQL datasource --> CR
    SUB -. definida en .-> ORI
  end

  subgraph UserFlow[Flujo usuario y IA]
    FE["Frontend estatico\nHTML+JS+Tailwind+Leaflet+ThreeJS+ChartJS\n8080"]
    API["FastAPI backend\n8000"]
    ML["Modelo ML\nserving predicciones"]
    LLM["LM Studio + Gemma\nhttp://host.docker.internal:1234/v1"]
    FE -- HTTPS/HTTP JSON --> API
    API -- NGSI-LD query --> ORI
    API -- feature extraction --> CR
    API -- inferencia --> ML
    API -- OpenAI-compatible API --> LLM
    API -- JSON respuesta --> FE
  end

  MDB(["MongoDB\n27017"])
  ORI -- persistencia interna --> MDB
```

---

## 6. Diagrama del Modelo de Datos

```mermaid
graph TD
  SI[GBFSStation / station_information]
  SS[GBFSStationStatus / station_status]
  FB[GBFSFreeBikeStatus / free_bike_status]
  SYS[GBFSSystemInformation / system_information]
  GEO[GBFSGeofencingZone / geofencing_zones]
  MSP[MobilityStation / BicycleParkingStation]
  TR[Trip / OSLO Trip]
  DEV[Device]
  WEA[WeatherObserved]

  SS -->|refStation hub relation| SI
  FB -->|refStation hub relation| SI
  MSP -->|refGBFSStation hub relation| SI
  TR -->|refOrigin hub relation| SI
  TR -->|refDestination hub relation| SI
  TR -->|refVehicle hub relation| DEV
  WEA -->|refDevice official| DEV
  SI -->|refWeather hub relation| WEA
  DEV -->|refStation hub relation| SI
```

---

## 7. Conclusiones Técnicas

Smart Mobility Hub materializa una visión de **interoperabilidad abierta y escalabilidad multi-región** mediante el stack FIWARE nativo. Orion-LD (NGSI-LD) actúa como fuente única de verdad para contexto operativo en tiempo real. IoT Agent MQTT traduce sensores a entidades semánticas. QuantumLeap + CrateDB acumulan series temporales para ML e histórico. Grafana Cloud expone dashboards parametrizados. FastAPI orquesta lógica de negocio, function calling para LLM y predicciones.

El despliegue reproducible mediante Docker Compose en un único comando, sin configuración manual, asegura portabilidad a nuevas ciudades. La arquitectura es agnóstica a geografía pero adaptada a fenómenos locales (viento para A Coruña). Compliance con NGSI-LD, GBFS y OSLO garantiza futuras integraciones con sistemas intermodales y ecosistemas de datos abiertos urbanos.

---

*Documento generado como parte de la Práctica 3 — Gestión de Datos en Entornos Inteligentes, Universidade da Coruña.*
