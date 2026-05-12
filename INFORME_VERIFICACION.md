# INFORME DE VERIFICACIÓN - Smart Mobility Hub

**Fecha última actualización**: 2026-05-12

---

## Stack FIWARE

| Servicio | Puerto | Versión |
|----------|--------|---------|
| MongoDB | 27017 | 4.4 |
| Orion-LD | 1026 | 1.6.0 |
| Mosquitto | 1883 | 2.0 |
| IoT Agent JSON MQTT | 4041 | 3.4.0 |
| CrateDB | 5432 | 5.4.3 |
| QuantumLeap | 8668 | 1.0.0 |
| Grafana | 3000 | 10.2.0 |
| FastAPI backend | 8000 | 0.115.12 |
| Frontend Nginx | 8081 | — |

---

## Entidades NGSI-LD en Orion-LD

| Tipo | Cantidad | Contexto |
|------|----------|---------|
| `station_information` | 1 | dataModel.GBFS |
| `station_status` | 15 | dataModel.GBFS |
| `Device` | 15 | dataModel.Device |
| `BicycleParkingStation` | 15 | dataModel.OSLO |
| `Trip` | 5 | OSLO Trips AP (data.vlaanderen.be) |
| `free_bike_status` | 1 | dataModel.GBFS |
| `system_information` | 1 | dataModel.GBFS |
| `geofencing_zones` | 1 | dataModel.GBFS |
| `WeatherObserved` | 1 | dataModel.Weather |
| **Total** | **55** | |

---

## CrateDB (datos históricos — 10 días)

| Tabla | Filas | Rango |
|-------|-------|-------|
| `crate.etstation_status` | 14.400 | últimos 10 días, 15 min/estación |
| `crate.etweatherobserved` | 240 | últimos 10 días, 1 h |
| `crate.trips` | 200 | últimos 10 días |
| `mtsmartmobilityhub.etstation_status` | creciente | datos live de QuantumLeap |

---

## Suscripciones Orion-LD activas

| ID | Origen | Destino |
|----|--------|---------|
| `urn:ngsi-ld:Subscription:station_status_to_quantumleap` | station_status | QuantumLeap |
| `urn:ngsi-ld:Subscription:weatherobserved_to_quantumleap` | WeatherObserved | QuantumLeap |
| `urn:ngsi-ld:Subscription:trip_to_quantumleap` | Trip | QuantumLeap |
| `urn:ngsi-ld:Subscription:station_status_alerts` | station_status | Backend /api/alerts/notify |

---

## Pipeline IoT

```
iot-simulator → MQTT /bicicoruna/{STATION_ID}/attrs
  → Mosquitto :1883
  → IoT Agent JSON MQTT :4041
  → Orion-LD PATCH station_status:acoruna:{STATION_ID}
  → Suscripción → QuantumLeap → CrateDB
  → Suscripción → Backend alertas (SSE)
```

Intervalo: 30 s por estación. Atributos: `num_bikes_available`, `num_docks_available`, `last_reported`.

---

## Conformidad con Smart Data Models

| Entidad | Modelo oficial | Conforme |
|---------|---------------|---------|
| `station_information` | dataModel.GBFS | ✅ |
| `station_status` | dataModel.GBFS | ✅ (diseño por-estación, adaptación IoT documentada) |
| `free_bike_status` | dataModel.GBFS | ✅ |
| `system_information` | dataModel.GBFS | ✅ |
| `geofencing_zones` | dataModel.GBFS | ✅ |
| `BicycleParkingStation` | dataModel.OSLO | ✅ |
| `Device` | dataModel.Device | ✅ (`controlledProperty: ["occupancy"]`) |
| `WeatherObserved` | dataModel.Weather | ✅ |
| `Trip` | OSLO Trips AP (vlaanderen.be) | ✅ (no está en dataModel.OSLO; usa AP oficial) |

### Nota sobre `station_status`

El esquema oficial de Smart Data Models define `station_status` como una entidad feed única con `data.stations[]` (igual que `station_information`). Esta plataforma usa en cambio **una entidad por estación** con los atributos al nivel raíz. Esta es la adaptación estándar en despliegues FIWARE IoT: permite que el IoT Agent actualice cada estación individualmente vía MQTT, y que las suscripciones de Orion detecten cambios por estación. La desviación está documentada en `data_model.md`.

---

## Comandos de operación

```bash
# Levantar todo
docker compose up -d

# Seed inicial (idempotente)
ORION_URL=http://localhost:1026 python3 scripts/seed_current_data.py

# Re-seed histórico (requiere vaciar las tablas primero)
# docker exec cratedb crash --command "DELETE FROM crate.etstation_status; ..."
python3 scripts/seed_historical_data.py

# Tests
PYTHONPATH=backend .venv/bin/pytest tests/test_api.py -v

# Logs IoT
docker compose logs -f iot-agent-mqtt
docker compose logs -f iot-simulator

# Bajar
docker compose down
```
