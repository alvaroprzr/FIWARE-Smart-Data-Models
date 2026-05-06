# 📋 Smart Mobility Hub - Deployment & Access Guide

## 🚀 Estado Actual
✅ **Stack FIWARE completamente operacional**
✅ **Modelos ML entrenados y en producción (MAE: 2.13 bikes)**
✅ **Suscripciones activas: Orion → QuantumLeap → CrateDB**
✅ **130K+ registros históricos en CrateDB**
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
- **Endpoints**: /health, /api/stations, /api/forecast, /api/chat, /api/weather, /api/heatmap

### Grafana (Dashboards)
- **URL**: http://localhost:3000
- **Usuario/Contraseña**: admin / admin
- **Datasource**: CrateDB provisionado

### Orion-LD (Context Broker)
- **URL**: http://localhost:1026
- **API**: NGSI-LD REST

### CrateDB (Series Temporales)
- **Puerto**: 5432 (PostgreSQL)
- **Usuario**: crate
- **Base de datos**: crate
- **Tablas**: etstation_status (130K+), etweatherobserved (2K+)

### IoT Agent MQTT
- **URL**: http://localhost:4041
- **Función**: Mapeo MQTT → NGSI-LD

---

## 🔧 Tareas Comunes

### Entrenar modelos
```bash
PYTHONPATH=backend .venv/bin/python3 backend/ml/train.py
docker cp backend/ml/model_*.joblib fastapi-backend:/app/ml/
docker restart fastapi-backend
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
| MAE t+30min | 2.134 ✓ |
| MAE t+60min | 1.875 ✓ |
| Tests | 7/7 ✓ |
| Filas CrateDB | 130K+ |
| Suscripciones | 3 activas |

