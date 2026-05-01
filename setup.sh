#!/bin/bash
set -e

ORION_URL=${ORION_URL:-http://localhost:1026}
IOTAGENT_URL=${IOTAGENT_URL:-http://localhost:4041}
SERVICE=${SERVICE:-smartmobilityhub}
SERVICEPATH=${SERVICEPATH:-/acoruna}

echo "Esperando a que Orion-LD esté disponible..."
until curl -sf "${ORION_URL}/version" > /dev/null; do
  sleep 3
done

echo "Orion listo. Registrando IoT Agent service group..."
# Paso 5: Registrar service group del IoT Agent
HTTP_CODE=$(curl -s -o /dev/stderr -w "%{http_code}" -X POST ${IOTAGENT_URL}/iot/services \
  -H "Content-Type: application/json" \
  -d '{
    "services": [
      {
        "apikey": "bicicoruna",
        "cbroker": "http://orion-ld:1026",
        "entity_type": "station_status",
        "resource": "/bicicoruna"
      }
    ]
  }') || true

# If IoT Agent registration returns 201 or 409, continue; else print and continue
if [[ "$HTTP_CODE" == "201" || "$HTTP_CODE" == "409" ]]; then
  echo "IoT Agent service group registered (or already exists): ${HTTP_CODE}"
else
  echo "IoT Agent registration returned HTTP ${HTTP_CODE} (continuing)"
fi

# Paso 6: Crear suscripciones en Orion-LD -> QuantumLeap
create_subscription() {
  PAYLOAD="$1"
  DESC="$2"
  echo "Creando suscripción ${DESC}..."
  CODE=$(curl -s -o /dev/stderr -w "%{http_code}" -X POST ${ORION_URL}/ngsi-ld/v1/subscriptions \
    -H "Content-Type: application/ld+json" \
    -d "${PAYLOAD}" ) || true
  if [[ "$CODE" == "201" || "$CODE" == "409" ]]; then
    echo "Suscripción ${DESC} creada o ya existía: ${CODE}"
  else
    echo "Aviso: creación de suscripción ${DESC} devolvió HTTP ${CODE} (continuando)"
  fi
}

# station_status -> QuantumLeap (paso 6)
PAYLOAD_STATION='{
    "id": "urn:ngsi-ld:Subscription:station_status_to_quantumleap",
    "type": "Subscription",
    "name": "station_status_changes_to_quantumleap",
    "description": "Notificar cambios de station_status para persistencia historica en QuantumLeap",
    "entities": [
      { "type": "station_status" }
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
create_subscription "$PAYLOAD_STATION" "station_status -> QuantumLeap"

# WeatherObserved -> QuantumLeap (paso 6.b)
PAYLOAD_WEATHER='{
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
create_subscription "$PAYLOAD_WEATHER" "WeatherObserved -> QuantumLeap"

# Trip -> QuantumLeap (paso 6.c)
PAYLOAD_TRIP='{
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
create_subscription "$PAYLOAD_TRIP" "Trip -> QuantumLeap"

echo "Cargando datos de prueba..."
echo "- seed_current_data.py es idempotente y actualiza/crea entidades"
echo "- seed_historical_data.py solo carga si CrateDB está vacío para evitar duplicados"
python3 scripts/seed_current_data.py || echo "seed_current_data.py exited with non-zero code"
python3 scripts/seed_historical_data.py || echo "seed_historical_data.py exited with non-zero code"

echo "Setup completado. Accede a http://localhost:8081"
