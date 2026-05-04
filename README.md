# Smart Mobility Hub · BiciCoruña Smart

Plataforma inteligente FIWARE para monitorización, análisis y predicción de sistemas de bicicletas compartidas. Stack multi-componente (Orion-LD, IoT Agent MQTT, QuantumLeap, CrateDB, Grafana, FastAPI, LLM local) desplegado con Docker Compose en una ciudad piloto (A Coruña) escalable a múltiples ciudades.

---

## Repositorio GitHub

```
https://github.com/alvaroprzr/FIWARE-Smart-Data-Models
```

---

## Requisitos previos

### Antes de instalar
- **Docker Engine (v24+)** o Docker Desktop con Docker Compose plugin (v2.0+)
- **Git 2.0+**
- **Python 3.11+** y pip (solo para instalación inicial)
- **LM Studio** (https://lmstudio.ai): descargar modelo Gemma 2B o 7B y mantener el servidor local activo en **puerto 1234** durante toda la sesión

### Hardware mínimo recomendado
- 8 GB RAM disponibles (los servicios Docker usan ~3-4 GB)
- 20 GB de espacio en disco (imágenes Docker + volúmenes)
- CPU multi-núcleo

---

## Instalación inicial (primera vez)

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/alvaroprzr/FIWARE-Smart-Data-Models.git
cd FIWARE-Smart-Data-Models
```

### Paso 2: Activar LM Studio localmente

⚠️ **Crítico**: Abre **LM Studio**, descarga el modelo **Gemma 2B** o **7B** (si no lo tienes aún), selecciónalo e inicia el **servidor local** en **puerto 1234**. Deberías ver:

```
Server running at http://localhost:1234
```

**Mantén esta terminal abierta durante todo el proceso de instalación y todos los futuros arranques.** El backend Docker necesita conectarse a este servidor para el asistente IA.

### Paso 3: Crear entorno virtual y dependencias locales

Crea un entorno virtual Python para los scripts de setup y datos de prueba:

```bash
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias mínimas para scripts de setup
pip install requests psycopg2-binary
```

⚠️ **Nota**: Este entorno local (`.venv`) **solo es necesario para la instalación inicial**. Se puede eliminar después si lo deseas. El backend en Docker tiene sus propias dependencias (ver `backend/requirements.txt`).

### Paso 4: Levantar todos los servicios Docker

```bash
docker compose up -d --build
```

Este comando arranca en segundo plano todos los servicios: MongoDB, Orion-LD, Mosquitto, IoT Agent MQTT, CrateDB, QuantumLeap, FastAPI backend, Grafana y frontend Nginx.

### Paso 5: Esperar a healthchecks y provisioning

Los servicios tardan **~60 segundos** en estar listos. Verifica el estado:

```bash
docker compose ps
```

Espera a que todos muestren estado `Up` o `healthy` (indicado con una marca verde en Docker Desktop).

### Paso 6: Ejecutar provisioning automático (setup)

Ahora configura automáticamente el IoT Agent, crea suscripciones y carga datos de prueba:

```bash
chmod +x setup.sh
./setup.sh
```

✅ **Qué hace este script** (es idempotente):
1. Registra el service group del IoT Agent en Orion-LD (si ya existe, lo ignora con HTTP 409)
2. Crea 3 suscripciones: `station_status` → QuantumLeap, `WeatherObserved` → QuantumLeap, `Trip` → QuantumLeap (si existen, las preserva)
3. Ejecuta `seed_current_data.py`: crea o actualiza las 15 estaciones y datos actuales en Orion-LD (idempotente)
4. Ejecuta `seed_historical_data.py`: carga 90 días de histórico en CrateDB **solo si las tablas están vacías** (para no duplicar al reiniciar)

**Duración**: ~2-3 minutos (especialmente `seed_historical_data.py`, que inserta ~130k filas).

### Paso 7: Entrenar modelo ML (dentro del contenedor)

Ahora entrena el modelo de predicción de demanda con los datos históricos:

```bash
docker compose exec fastapi-backend python ml/train.py
```

Este comando:
- Lee 90 días de histórico desde CrateDB
- Entrena 2 modelos RandomForest (30 min y 60 min)
- Persiste los modelos en `/backend/ml/` (montados como volumen)
- Habilita predicciones en los endpoints `/api/stations/{id}/forecast`

**Duración**: ~1-2 minutos.

### Paso 8: Verificar instalación

Comprueba que todo está en marcha:

```bash
# Backend
curl http://localhost:8000/health
# Respuesta esperada: {"status":"healthy"}

# Orion-LD
curl http://localhost:1026/version
# Respuesta: versión de Orion

# Frontend
open http://localhost:8081
# Deberías ver el mapa interactivo con 15 estaciones de A Coruña
```

✅ **Instalación completada.** Puedes acceder a:
- **Frontend interactivo**: http://localhost:8081
- **Grafana dashboards**: http://localhost:3000 (admin / admin)
- **API Swagger UI**: http://localhost:8000/docs
- **Orion-LD API**: http://localhost:1026/ngsi-ld/v1/entities
- **CrateDB admin**: http://localhost:4200

---


## Ejecución recurrente (cada vez que se reinicia)

Una vez completada la instalación inicial, cada vez que quieras arrancar la plataforma:

### Paso 1: Asegúrate de que LM Studio está activo

⚠️ **Obligatorio**: Abre LM Studio, selecciona el modelo Gemma y confirma que el servidor está activo en **http://localhost:1234**.

### Paso 2: Levantar los servicios

```bash
docker compose up -d
```

**Nota**: Sin `--build`. Solo se reconstruyen si cambias un Dockerfile o agregas dependencias Python en `backend/requirements.txt`. En caso de cambios:

```bash
docker compose up -d --build
```

### Paso 3: Esperar a healthchecks

```bash
docker compose ps
```

Espera ~60 segundos hasta que todos los servicios muestren `Up` o `healthy`.

### Paso 4: Verificar que los datos persisten

```bash
# Comprueba que las estaciones están en Orion
curl http://localhost:1026/ngsi-ld/v1/entities?type=station_status | head -c 300
# Deberías ver estaciones como ACORUNA-001, ACORUNA-002, etc.
```

✅ **Plataforma lista.** Accede a **http://localhost:8081**.

---

## Detener y limpiar

### Parada normal (datos persisten)

```bash
docker compose down
```

Detiene todos los contenedores pero **mantiene los volúmenes de datos** (MongoDB, CrateDB, Grafana). Los datos de estaciones, histórico y dashboards se conservan para el próximo arranque.

### Reset total (destructivo)

⚠️ **ADVERTENCIA**: Este comando elimina **TODOS los datos**. Úsalo solo si quieres empezar desde cero.

```bash
docker compose down -v
```

Esto borra:
- Todas las entidades en Orion-LD (estaciones, estado actual)
- Histórico de 90 días en CrateDB
- Dashboards y configuración de Grafana
- Datos de MongoDB

Para restaurar el estado, vuelve a ejecutar desde el Paso 6 de la instalación inicial (`./setup.sh`).

---

### 5. (OPCIONAL) Pasos manuales alternativos

Si prefieres configurar manualmente sin el script `setup.sh`, sigue los pasos a continuación. **Esto reemplaza completamente el Paso 6** de la instalación inicial.

⚠️ **No ejecutes ambos**: si usas esta vía, sáltate `./setup.sh` para evitar suscripciones duplicadas.

### Paso A: Registrar el service group del IoT Agent

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

### Paso B: Crear la suscripción Orion-LD → QuantumLeap (station_status)

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

### Paso C: Crear la suscripción Orion-LD → QuantumLeap (WeatherObserved)

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

### Paso D: Crear la suscripción Orion-LD → QuantumLeap (Trip)
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

### Paso E: Cargar datos actuales de prueba

```bash
source .venv/bin/activate  # Si no está activado
python scripts/seed_current_data.py
```

Este script inyecta las 15 estaciones y datos actuales en Orion-LD. Envía automáticamente los headers FIWARE requeridos (`Fiware-Service`, `Fiware-ServicePath`).

### Paso F: Cargar datos históricos de prueba

```bash
python scripts/seed_historical_data.py
```

Carga 90 días de histórico en CrateDB (~130k filas). El script verifica si ya existen datos y omite la carga si las tablas no están vacías.

### Paso G: Entrenar modelo ML

```bash
docker compose exec fastapi-backend python ml/train.py
```

### Acceso a la aplicación

Todos los endpoints están listos:

```
Frontend:     http://localhost:8081
Grafana:      http://localhost:3000
API Swagger:  http://localhost:8000/docs
```

---

## URLs de acceso a cada servicio

| Servicio | URL | Credenciales | Propósito |
|---|---|---|---|
| **Frontend** | http://localhost:8081 | Sin autenticación | Interfaz ciudadana: mapa, predicciones, chat |
| **Grafana** | http://localhost:3000 | admin / admin | Dashboards analíticos y operativos |
| **API Swagger** | http://localhost:8000/docs | Sin autenticación | Documentación interactiva de endpoints REST |
| **Orion-LD** | http://localhost:1026/ngsi-ld/v1/entities | Sin autenticación | Consultas NGSI-LD directas (avanzado) |
| **CrateDB Admin** | http://localhost:4200 | Sin credenciales | Gestor de base de datos (avanzado) |
| **QuantumLeap** | http://localhost:8668/v2/entities | Sin autenticación | API de series temporales (avanzado) |
| **IoT Agent** | http://localhost:4041/iot/about | Sin autenticación | Estado del adaptador IoT (avanzado) |
| **MQTT** | mqtt://localhost:1883 | Anónimo | Broker de sensores (avanzado) |

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

## Guía de troubleshooting

### Problema: "Port 1234 already in use" o LM Studio no accesible

**Causa**: LM Studio no está corriendo o está en otro puerto.  
**Solución**: Abre LM Studio, verifica que muestra "Server running at http://localhost:1234", y mantén la ventana abierta.

### Problema: "No module named 'requests'" al ejecutar setup.sh

**Causa**: El entorno virtual no fue activado o las dependencias no están instaladas.  
**Solución**:

```bash
source .venv/bin/activate
pip install requests psycopg2-binary
./setup.sh
```

### Problema: Servicios no healthy después de 2 minutos

**Causa**: Los healthchecks fallan porque un servicio previo no inició.  
**Solución**:

```bash
# Ver logs detallados
docker compose logs -f

# Reintentar
docker compose down
docker compose up -d --build
```

### Problema: "Datos históricos ya presentes" pero quiero refrescar

**Causa**: `seed_historical_data.py` detectó tablas no vacías.  
**Solución**: Ejecuta reset total y reinstala:

```bash
docker compose down -v
docker compose up -d --build
./setup.sh
docker compose exec fastapi-backend python ml/train.py
```

### Problema: Predicciones no disponibles en `/api/stations/{id}/forecast`

**Causa**: El modelo ML no fue entrenado.  
**Solución**:

```bash
docker compose exec fastapi-backend python ml/train.py
```

---

## Referencia: Sintaxis Docker moderno

✅ **Correcto** (espacio, sin guion):

```bash
docker compose up -d
docker compose ps
docker compose down
docker compose exec fastapi-backend bash
```

❌ **Antiguo** (guion, no recomendado):

```bash
docker-compose up -d  # ← No uses esta forma
```

Todos los comandos en este README usan la sintaxis moderna.

---

## Actualizar dependencias de Python del backend

Si modificas `backend/requirements.txt`, reconstruye el contenedor:

```bash
docker compose up -d --build fastapi-backend
```

Para generar un nuevo `requirements.txt` desde el entorno local:

```bash
source .venv/bin/activate
pip freeze > backend/requirements.txt
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
# Instalar dependencias de testing (activar venv primero si no está activado)
source .venv/bin/activate
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