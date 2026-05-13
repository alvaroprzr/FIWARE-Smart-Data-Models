# 📋 Smart Mobility Hub - Deployment & Access Guide

## 🚀 Estado Actual
✅ **Stack FIWARE completamente operacional**
✅ **Modelos ML entrenados y en producción (MAE t+30: 2.13 bikes, MAE t+60: 1.88 bikes)**
✅ **Suscripciones activas: Orion → QuantumLeap → CrateDB**
✅ **~14.600 registros históricos en CrateDB (seed 10 días)**
✅ **Tests: 7/7 passing**

---

## 📍 Acceso a Componentes

### Frontend (Usuario final)
- **URL**: http://localhost:8081
- **Descripción**: Interfaz web responsiva con mapa interactivo
- **Características**: Selector ciudad, chat IA, gráficas

### API Backend
- **URL**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Endpoints principales**: `/health`, `/api/stations`, `/api/stations/{id}/status`, `/api/stations/{id}/forecast`, `/api/chat`, `/api/weather`, `/api/weather/correlation`, `/api/weather/trips/heatmap`, `/api/alerts/favorite` (POST/DELETE), `/api/alerts/favorites`, `/api/alerts/stream` (SSE), `/api/alerts/notify`, `/api/train`

### Grafana (Dashboards)
- **URL**: http://localhost:8081/grafana/
- **Acceso**: anónimo (sin contraseña)
- **Datasource**: CrateDB provisionado

### Orion-LD (Context Broker)
- **URL**: http://localhost:1026
- **API**: NGSI-LD REST

### CrateDB (Series Temporales)
- **Puerto**: 5432 (PostgreSQL)
- **Usuario**: crate
- **Base de datos**: crate
- **Tablas**: etstation_status (~14.400), etweatherobserved (264), trips (200+)

### IoT Agent MQTT
- **URL**: http://localhost:4041
- **Función**: Mapeo MQTT → NGSI-LD

---

## 🔧 Tareas Comunes

### Entrenar modelos
```bash
curl -X POST http://localhost:8000/api/train
# Respuesta esperada: {"status":"ok","models":["model_30","model_60"],"model_used":"random_forest"}
```

### Seedear datos
```bash
ORION_URL=http://localhost:1026 python3 scripts/seed_current_data.py
```

### Ejecutar tests
```bash
PYTHONPATH=backend .venv/bin/pytest tests/test_api.py -v
```

### Ver logs
```bash
docker compose logs -f fastapi-backend
```

### Detener stack
```bash
docker compose down
```

---

## 📊 Ejemplos API

### Estado de estación
```bash
curl "http://localhost:8000/api/stations/ACORUNA-001/status" | jq .
```

### Predicción 30/60 minutos
```bash
curl "http://localhost:8000/api/stations/ACORUNA-001/forecast" | jq .
# "model_used": "random_forest" ✓
```

### Chat IA
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"city":"acoruna","message":"¿Dónde hay bicis?"}'
```

### Heatmap de viajes
```bash
curl "http://localhost:8000/api/weather/trips/heatmap" | jq '. | length'
```

---

## 📈 Desempeño

| Métrica | Valor |
|---------|-------|
| MAE t+30min | 2.134 (PRD objetivo: <2) |
| MAE t+60min | 1.875 ✓ |
| Tests | 7/7 ✓ |
| Filas CrateDB | ~14.600 seed + live |
| Suscripciones | 4 activas |

