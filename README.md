# Smart Mobility Hub · BiciCoruña Smart

Plataforma inteligente FIWARE para monitorización, análisis y predicción de sistemas de bicicletas compartidas. Stack multi-componente (Orion-LD, IoT Agent MQTT, QuantumLeap, CrateDB, Grafana, FastAPI, LLM local) desplegado con Docker Compose en una ciudad piloto (A Coruña) escalable a múltiples ciudades.

---

## Repositorio GitHub

```
https://github.com/TU_USUARIO/smart-mobility-hub
```

---

## Requisitos previos

- **Docker Desktop (v24+)** o Docker Engine + Docker Compose plugin
- **Git**
- **LM Studio** (https://lmstudio.ai) con el modelo Gemma 2B o 7B descargado y servidor local activo en **puerto 1234**
- **Python 3.11+** y pip (solo para ejecutar los scripts de datos de prueba)

---

## Estructura del repositorio

```
smart-mobility-hub/
├── backend/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
├── iot/
│   ├── mqtt_simulator.py
│   └── config.json
├── mosquitto/
│   └── mosquitto.conf
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── cratedb.yaml
├── scripts/
│   ├── seed_current_data.py
│   ├── seed_historical_data.py
│   └── requirements.txt
├── docker-compose.yml
├── .gitignore
├── requirements.txt
├── README.md
├── PRD.md
├── data_model.md
├── architecture.md
└── APPLICATION.md
```

---

## Puesta en marcha paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/smart-mobility-hub.git
cd smart-mobility-hub
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

### 5. Registrar el service group del IoT Agent

```bash
curl -X POST http://localhost:4041/iot/services \
  -H "Content-Type: application/json" \
  -H "Fiware-Service: smartmobilityhub" \
  -H "Fiware-ServicePath: /acoruna" \
  -d '{
    "services": [
      {
        "apikey": "bicicoruna-key",
        "cbroker": "http://orion-ld:1026",
        "entity_type": "station_status",
        "resource": "/bicicoruna"
      }
    ]
  }'
```

Respuesta esperada: HTTP 201 (Created).

### 6. Crear la suscripción Orion-LD → QuantumLeap

```bash
curl -X POST http://localhost:1026/ngsi-ld/v1/subscriptions \
  -H "Content-Type: application/ld+json" \
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

### 7. Cargar datos actuales de prueba

```bash
python scripts/seed_current_data.py
```

Este script inyecta entidades de ejemplo (`station_status`, `station_information`) en Orion-LD para la ciudad piloto (A Coruña).

### 8. Cargar datos históricos de prueba

```bash
python scripts/seed_historical_data.py
```

Este script inserta series temporales de ejemplo en CrateDB para permitir análisis histórico y visualizaciones en Grafana.

### 9. Acceder a la aplicación

La aplicación está lista. Abre tu navegador en:

```
http://localhost:8080
```

Verás el mapa interactivo con las estaciones de bicicletas, datos en tiempo real y el asistente conversacional IA.

---

## URLs de acceso a cada servicio

| Servicio | URL | Credenciales |
|---|---|---|
| Frontend | http://localhost:8080 | Sin autenticación |
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

## Generación de requirements.txt

Para actualizar la lista de dependencias de Python del backend:

```bash
cd backend && pip freeze > ../requirements.txt
```

---

## Stack tecnológico

- **Orion-LD 1.6.0** — Context Broker NGSI-LD nativo
- **IoT Agent MQTT 3.4.0** — Adaptador de protocolo MQTT → NGSI-LD
- **QuantumLeap 0.9.0** — Motor de series temporales
- **CrateDB 5.4.3** — Base de datos analítica para históricos
- **MongoDB 6.0** — Almacén persistente de Orion-LD
- **Mosquitto 2.0** — Broker MQTT
- **FastAPI** — Backend Python para orquestación, consultas y IA
- **Gemma 2B/7B (LM Studio)** — LLM local para asistente conversacional
- **Grafana 10.2.0** — Dashboards operativos y analíticos
- **Frontend estatico** — HTML + JavaScript + Tailwind CSS + Leaflet + ThreeJS + ChartJS
- **Docker Compose** — Orquestación de contenedores
- **NGSI-LD** — Estándar de datos (Smart Data Models, GBFS, OSLO)

---

## Documentación del proyecto

Consulta los siguientes documentos para entender la arquitectura, requisitos y modelo de datos:

- **[PRD.md](PRD.md)** — Product Requirements Document con historias de usuario, objetivos y funcionalidades
- **[data_model.md](data_model.md)** — Modelo NGSI-LD completo (entidades, atributos, relaciones, contexts)
- **[architecture.md](architecture.md)** — Arquitectura técnica, flujos de datos, docker-compose, configuraciones
- **[APPLICATION.md](APPLICATION.md)** — Guía de uso de la interfaz de usuario

---

**Última actualización:** 2026-04-22  
**Estado:** Production-ready