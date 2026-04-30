# Smart Mobility Hub · BiciCoruña Smart

Plataforma inteligente FIWARE para monitorización, análisis y predicción de sistemas de bicicletas compartidas. Stack multi-componente (Orion-LD, IoT Agent MQTT, QuantumLeap, CrateDB, Grafana, FastAPI, LLM local) desplegado con Docker Compose en una ciudad piloto (A Coruña) escalable a múltiples ciudades.

---

## Repositorio GitHub

```
https://github.com/alvaroprzr/FIWARE-Smart-Data-Models
```

---

## Requisitos previos

- **Docker Desktop (v24+)** o Docker Engine + Docker Compose plugin
- **Git**
- **LM Studio** (https://lmstudio.ai) con el modelo Gemma 2B o 7B descargado y servidor local activo en **puerto 1234**
- **Python 3.11+** y pip (solo para ejecutar los scripts de datos de prueba)

---

## Puesta en marcha paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/alvaroprzr/FIWARE-Smart-Data-Models.git
cd FIWARE-Smart-Data-Models
```

### 2. Iniciar LM Studio con Gemma

Abre **LM Studio**, descarga el modelo **Gemma 2B** o **7B** (si aún no lo tienes), selecciónalo y activa el **servidor local** en **puerto 1234**. Deberías ver:

```
Server running at http://localhost:1234
```

Mantén esta terminal abierta durante toda la sesión.

### 3. Levantar todos los servicios

```bash
docker-compose up -d --build
```

Este comando arranca en segundo plano: MongoDB, Orion-LD, Mosquitto, IoT Agent MQTT, CrateDB, QuantumLeap, FastAPI backend, Grafana y frontend.

### 4. Esperar a que los healthchecks pasen

Los servicios con healthcheck (Orion-LD, IoT Agent, CrateDB) tardan **~60 segundos** en reportar estado `healthy`. Verifica el estado:

```bash
docker-compose ps
```

Espera a que todos los servicios muestren estado `Up` (o `healthy` si tienen healthcheck).

### 5. Configuración automática (recomendado)

Para automatizar el registro del IoT Agent, crear las suscripciones y cargar datos de prueba, ejecuta el script de setup:

```bash
chmod +x setup.sh
./setup.sh
```

Este script es **idempotente**: si una suscripción ya existe (HTTP 409), continúa sin error. Además:
1. `seed_current_data.py` crea o actualiza las entidades actuales de forma segura
2. `seed_historical_data.py` solo carga histórico si CrateDB está vacío, para no duplicar series al reiniciar el entorno

Se encarga de:
1. Esperar a que Orion-LD esté disponible
2. Registrar el service group del IoT Agent
3. Crear las 3 suscripciones principales (station_status, WeatherObserved, Trip)
4. Cargar datos de prueba iniciales

Si quieres repetir el histórico desde cero, elimina los volúmenes con `docker-compose down -v` antes de volver a ejecutar el setup.

Luego puedes acceder a la aplicación en **http://localhost:8081**.

---

### 5. (OPCIONAL) Pasos manuales alternativos

Si prefieres configurar manualmente sin el script setup.sh, sigue los pasos 5.a – 5.d.

### 5.a Registrar el service group del IoT Agent

```bash
curl -X POST http://localhost:4041/iot/services \
  -H "Content-Type: application/json" \
  -H "Fiware-Service: smartmobilityhub" \
  -H "Fiware-ServicePath: /acoruna" \
  -d '{
    "services": [
      {
        "apikey": "bicicoruna",
        "cbroker": "http://orion-ld:1026",
        "entity_type": "station_status",
        "resource": "/bicicoruna"
      }
    ]
  }'
```

Respuesta esperada: HTTP 201 (Created).

### 5.b Crear la suscripción Orion-LD → QuantumLeap

```bash
curl -X POST http://localhost:1026/ngsi-ld/v1/subscriptions \
  -H "Content-Type: application/ld+json" \
  -H "Fiware-Service: smartmobilityhub" \
  -H "Fiware-ServicePath: /acoruna" \
  -d '{
    "id": "urn:ngsi-ld:Subscription:station_status_to_quantumleap",
    "type": "Subscription",
    "name": "station_status_changes_to_quantumleap",
    "description": "Notificar cambios de station_status para persistencia historica en QuantumLeap",
    "entities": [
      {
        "type": "station_status"
      }
    ],
    "watchedAttributes": [
      "num_bikes_available",
      "num_docks_available",
      "is_renting",
      "is_returning",
      "last_reported"
    ],
    "notification": {
      "attributes": [
        "num_bikes_available",
        "num_docks_available",
        "is_renting",
        "is_returning",
        "last_reported",
        "refStation"
      ],
      "endpoint": {
        "uri": "http://quantumleap:8668/v2/notify",
        "accept": "application/json"
      }
    },
    "throttling": 1,
    "@context": [
      "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
    ]
  }'
```

Respuesta esperada: HTTP 201 (Created) con Location header.

### 5.c Suscripción Orion-LD → QuantumLeap: WeatherObserved

```bash
curl -X POST http://localhost:1026/ngsi-ld/v1/subscriptions \
  -H "Content-Type: application/ld+json" \
  -H "Fiware-Service: smartmobilityhub" \
  -H "Fiware-ServicePath: /acoruna" \
  -d '{
    "id": "urn:ngsi-ld:Subscription:weatherobserved_to_quantumleap",
    "type": "Subscription",
    "name": "weatherobserved_changes_to_quantumleap",
    "description": "Notificar cambios de WeatherObserved para persistencia historica en QuantumLeap",
    "entities": [
      { "type": "WeatherObserved" }
    ],
    "watchedAttributes": ["temperature","windSpeed","dateObserved"],
    "notification": {
      "attributes": ["temperature","windSpeed","dateObserved","location","refDevice"],
      "endpoint": { "uri": "http://quantumleap:8668/v2/notify", "accept": "application/json" }
    },
    "throttling": 5,
    "@context": [
      "https://smartdatamodels.org/context.jsonld",
      "https://raw.githubusercontent.com/smart-data-models/dataModel.Weather/master/context.jsonld"
    ]
  }'
```

### 5.d Suscripción Orion-LD → QuantumLeap: Trip
```bash
curl -X POST http://localhost:1026/ngsi-ld/v1/subscriptions \
  -H "Content-Type: application/ld+json" \
  -H "Fiware-Service: smartmobilityhub" \
  -H "Fiware-ServicePath: /acoruna" \
  -d '{
    "id": "urn:ngsi-ld:Subscription:trip_to_quantumleap",
    "type": "Subscription",
    "name": "trip_changes_to_quantumleap",
    "description": "Notificar cambios de Trip para persistencia historica en QuantumLeap",
    "entities": [
      { "type": "Trip" }
    ],
    "watchedAttributes": ["departureTime","arrivalTime","refOrigin","refDestination"],
    "notification": {
      "attributes": ["departureTime","arrivalTime","refOrigin","refDestination"],
      "endpoint": { "uri": "http://quantumleap:8668/v2/notify", "accept": "application/json" }
    },
    "throttling": 5,
    "@context": [
      "https://data.vlaanderen.be/doc/applicatieprofiel/mobiliteit-trips-en-aanbod/erkendestandaard/2020-04-23/context/mobiliteit-trips-en-aanbod-ap.jsonld"
    ]
  }'
```

### 5.e Cargar datos actuales de prueba
```bash
python scripts/seed_current_data.py
```

Este script inyecta entidades de ejemplo (`station_status`, `station_information`) en Orion-LD para la ciudad piloto (A Coruña).

**Nota:** El script debe enviar los headers FIWARE `Fiware-Service: smartmobilityhub` y `Fiware-ServicePath: /acoruna` en todas las peticiones POST/PATCH a Orion-LD al crear o actualizar entidades, para garantizar la consistencia con la configuración del IoT Agent.

### 5.f Cargar datos históricos de prueba

```bash
python scripts/seed_historical_data.py
```

Este script inserta series temporales de ejemplo en CrateDB para permitir análisis histórico y visualizaciones en Grafana.

### 6. Acceder a la aplicación

La aplicación está lista. Abre tu navegador en:

```
http://localhost:8081
```

Verás el mapa interactivo con las estaciones de bicicletas, datos en tiempo real y el asistente conversacional IA.

---

## URLs de acceso a cada servicio

| Servicio | URL | Credenciales |
|---|---|---|
| Frontend | http://localhost:8081 | Sin autenticación |
| API FastAPI (Swagger UI) | http://localhost:8000/docs | Sin autenticación |
| Grafana | http://localhost:3000 | admin / admin |
| Orion-LD (NGSI-LD API) | http://localhost:1026/ngsi-ld/v1/entities | Sin autenticación |
| CrateDB Admin UI | http://localhost:4200 | Sin credenciales |
| QuantumLeap | http://localhost:8668/v2/entities | Sin autenticación |
| IoT Agent (status) | http://localhost:4041/iot/about | Sin autenticación |
| MQTT Broker (Mosquitto) | mqtt://localhost:1883 | Anónimo permitido |

---

## Detener y limpiar el entorno

### Parar todos los servicios

```bash
docker-compose down
```

Los volúmenes de datos persisten. Los contenedores se detienen pero no se borran.

### Parar y borrar todo (reset total)

```bash
docker-compose down -v
```

Esto detiene los servicios y **elimina todos los volúmenes** (MongoDB, CrateDB, Grafana, etc.). Los datos se pierden. Úsalo cuando quieras empezar desde cero.

---

## Arquitectura del Frontend (Modularizado ES6)

El frontend utiliza una **arquitectura modularizada con 5 módulos ES6 independientes** (sin bundler), cargados directamente via `<script type="module">`. Esta arquitectura facilita el mantenimiento, escalabilidad y permite que cada módulo sea responsable de su dominio específico.

### Módulos del Frontend

| Módulo | Responsabilidad | Tamaño |
|--------|-----------------|--------|
| `js/utils.js` | Estado compartido (`appState`), configuración de ciudades, funciones utilitarias | 4.5 KB |
| `js/map.js` | Mapa Leaflet, carga de estaciones, marcadores, heatmap de viajes, predicciones | 13 KB |
| `js/chat.js` | Panel de chat, mensajería con LLM backend vía `/api/chat` | 2.1 KB |
| `js/3d-view.js` | Escena Three.js, barras animadas, raycasting, tooltip interactivo | 12 KB |
| `js/charts.js` | Gráfico doughnut de CO₂ ahorrado con plugin de etiqueta central | 3.0 KB |

### Flujo de inicialización

1. **`index.html`** carga CDN scripts (Leaflet, Chart.js, Three.js, Tailwind).
2. **Coordinador mínimo** en `<script type="module">`:
   - Importa los 5 módulos y `utils.js`.
   - Inicializa cada módulo: `initMap()`, `initChat()`, `initCharts()`, `init3DView()`.
   - Gestiona evento selector de ciudad y ciclo de refresh (30 segundos).
3. **Estado centralizado** via `appState` (exportado desde `utils.js`): todos los módulos leen/escriben el mismo estado.
4. **Comunicación inter-módulos**: mínima, a través de `appState` actualizado y funciones públicas (`updateStations()`, `updateChartsData()`, etc.).

### Características clave

- ✅ **ES6 Modules**: imports/exports estándar sin transpilación ni bundler
- ✅ **Estado compartido**: `appState` centralizado para evitar inconsistencias
- ✅ **Desacoplamiento**: cada módulo independiente y reemplazable
- ✅ **API correcta**: todos los módulos usan endpoints reales del backend:
  - `GET /api/stations?city={city}`
  - `GET /api/stations/{id}/status`
  - `GET /api/stations/{id}/forecast`
  - `GET /api/weather/trips/heatmap?city={city}`
  - `POST /api/chat` (body: `{city, message}`)
- ✅ **Ciclo de refresco**: 30 segundos para actualizar statuses y heatmap automáticamente
- ✅ **Manejo de errores**: try/catch en todas las peticiones, feedback de conexión online/offline

---

## Generación de requirements.txt

Para actualizar la lista de dependencias de Python del backend:

```bash
cd backend && pip freeze > ../requirements.txt
```

---

## Stack tecnológico
- **Orion-LD 1.6.0** — Context Broker NGSI-LD nativo
- **IoT Agent MQTT 3.4.0** — Adaptador de protocolo MQTT → NGSI-LD
- **QuantumLeap 1.0.0** — Motor de series temporales
- **CrateDB 5.4.3** — Base de datos analítica para históricos
- **MongoDB 4.4** — Almacén persistente de Orion-LD
- **Mosquitto 2.0** — Broker MQTT
- **FastAPI** — Backend Python para orquestación, consultas y IA
- **Gemma 2B/7B (LM Studio)** — LLM local para asistente conversacional
- **Grafana 10.2.0** — Dashboards operativos y analíticos
- **Frontend modularizado ES6** — 5 módulos independientes (utils, map, chat, 3d-view, charts) sin bundler, cargados via `<script type="module">`. Librerías: Tailwind CSS, Leaflet, Three.js, Chart.js
- **Docker Compose** — Orquestación de contenedores
- **NGSI-LD** — Estándar de datos (Smart Data Models, GBFS, OSLO)

---

## Testing del Backend

El backend incluye una suite completa de tests con pytest-asyncio que valida todos los endpoints API contra especificaciones NGSI-LD. Los tests usan mocks para aislar completamente los servicios externos (Orion, CrateDB, LM Studio).

### Ejecutar los tests

Desde el directorio raíz del proyecto:

```bash
# Instalar dependencias de testing (incluidas en requirements.txt)
cd backend && pip install -r requirements.txt

# Ejecutar tests con verbose output
pytest ../tests -v

# Ejecutar tests con short traceback (más legible)
pytest ../tests -v --tb=short

# Ejecutar un test específico
pytest ../tests/test_api.py::TestStations::test_get_stations -v
```

### Cobertura de tests

La suite incluye **7 tests** que cubren:

| Test | Endpoint | Descripción |
|------|----------|-------------|
| `test_health` | `GET /health` | Health check del backend |
| `test_get_stations` | `GET /api/stations?city=acoruna` | Lista de estaciones |
| `test_get_station_status` | `GET /api/stations/{id}/status` | Estado dinámico de estación |
| `test_get_forecast` | `GET /api/stations/{id}/forecast` | Predicción de demanda (30/60 min) |
| `test_chat` | `POST /api/chat` | Asistente IA conversacional |
| `test_weather` | `GET /api/weather?city=acoruna` | Observaciones meteorológicas |
| `test_heatmap` | `GET /api/weather/trips/heatmap` | Heatmap de demanda de viajes |

### Mocking de servicios

- **OrionClient**: Devuelve datos NGSI-LD simulados (estaciones, estado, meteorología)
- **LLMClient**: Devuelve respuestas de chat sin tool_calls
- **CrateDBClient**: Devuelve listas vacías de heatmap

Todos los tests se ejecutan **sin contactar servicios externos**, garantizando velocidad y determinismo.

## Documentación del proyecto

Consulta los siguientes documentos para entender la arquitectura, requisitos y modelo de datos:

- **[PRD.md](PRD.md)** — Product Requirements Document con historias de usuario, objetivos y funcionalidades
- **[data_model.md](data_model.md)** — Modelo NGSI-LD completo (entidades, atributos, relaciones, contexts)
- **[architecture.md](architecture.md)** — Arquitectura técnica, flujos de datos, docker-compose, configuraciones
- **[APPLICATION.md](APPLICATION.md)** — Guía de uso de la interfaz de usuario

---

**Última actualización:** 2026-04-22  
**Estado:** MVP (Minimum Viable Product) - Demostración funcional para Práctica 3