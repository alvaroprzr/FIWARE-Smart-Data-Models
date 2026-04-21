# BiciCoruna Smart - FIWARE Smart Data Models

Proyecto academico de la Practica 3 (Gestion de Datos en Entornos Inteligentes) centrado en el escenario de bicicletas compartidas.

## Descripcion

BiciCoruna Smart es una plataforma para visualizar, analizar y predecir la disponibilidad de bicicletas compartidas usando estandares NGSI-LD y componentes FIWARE.

El sistema combina:

- Datos de estaciones y bicicletas (GBFS).
- Datos de movilidad urbana (OSLO).
- Datos meteorologicos para mejorar predicciones.
- Capa de visualizacion ciudadana y capa analitica.

## Objetivos

- Mostrar disponibilidad en tiempo real de bicis y anclajes por estacion.
- Predecir disponibilidad futura a 30-60 minutos.
- Ofrecer planificacion de rutas urbanas con informacion topografica.
- Exponer dashboards publicos de uso, demanda y sostenibilidad.
- Mantener un modelado interoperable basado en Smart Data Models.

## Arquitectura funcional

La arquitectura sigue un flujo de ingesta, contexto, historico y consumo:

1. Sensores/dispositivos y feeds generan eventos.
2. IoT Agent MQTT normaliza e ingiere datos.
3. Orion Context Broker mantiene el estado NGSI-LD en tiempo real.
4. QuantumLeap/CrateDB persiste series temporales para analitica y ML.
5. FastAPI expone APIs para frontend, analitica y asistente conversacional.
6. Frontend web muestra mapa, predicciones y dashboards.

## Smart Data Models

Entidades principales consideradas en el PRD:

- GBFSStation
- GBFSStationStatus
- GBFSFreeBikeStatus
- GBFSSystemInformation
- GBFSGeofencingZone
- MobilityStation
- Trip
- Device
- WeatherObserved

## Stack tecnologico

- FIWARE: Orion Context Broker, IoT Agent MQTT, QuantumLeap.
- Backend: FastAPI (Python).
- Frontend: HTML, JavaScript, Tailwind CSS.
- Visualizacion: Leaflet + OpenStreetMap, Chart.js, Three.js, Grafana.
- Datos/ML: Pandas, GeoPandas, Polars, scikit-learn, statsmodels.
- Despliegue: Docker Compose.

## Requisitos no funcionales clave

- Uso de NGSI-LD en toda la comunicacion de contexto.
- Interfaz responsiva para movil y escritorio.
- Actualizacion de disponibilidad con latencia maxima de 30 segundos.
- Carga inicial del mapa por debajo de 3 segundos.
- Despliegue completo con Docker Compose.

## Estructura actual del repositorio

En el estado actual, el repositorio contiene:

- PRD.md
- README.md
- .gitignore

## Puesta en marcha (base)

Este repositorio esta en fase inicial de documentacion. Cuando se anadan servicios y codigo, la ejecucion recomendada sera con Docker Compose.

Pasos base esperados:

1. Clonar el repositorio.
2. Definir variables de entorno en un archivo .env local.
3. Levantar servicios con Docker Compose.
4. Acceder al frontend y dashboards.

## Estado del proyecto

Fase actual: definicion funcional y documental a partir del PRD.

Proximo objetivo tecnico: incorporar estructura de codigo (backend, frontend y despliegue) alineada con las historias de usuario priorizadas.

## Referencia

Para el detalle funcional completo, revisar el documento PRD.md.