"""
Test fixtures for backend API tests.

Provides:
- mock_orion: Mock OrionClient with NGSI-LD data
- mock_llm: Mock LLMClient with simple responses
- client: AsyncClient for FastAPI testing
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest.fixture
def mock_orion():
    """
    Mock OrionClient that returns NGSI-LD compliant data.
    
    Returns dict-based mock data for:
    - station_information: Per-station entities with static catalog (station_id, name, capacity, location)
    - station_status: Dynamic status for individual stations (num_bikes, docks, etc.)
    - WeatherObserved: Current weather conditions
    """
    mock = AsyncMock()
    
    # Mock get_entities for station_information (per-station model)
    async def mock_get_entities(entity_type: str = None, **kwargs):
        if entity_type == "station_information":
            return [
                {
                    "type": "station_information",
                    "id": "urn:ngsi-ld:station_information:acoruna:ACORUNA-001",
                    "station_id": "ACORUNA-001",
                    "name": "María Pita",
                    "capacity": 20,
                    "location": {
                        "type": "GeoProperty",
                        "value": {"type": "Point", "coordinates": [-8.408, 43.372]},
                    },
                },
                {
                    "type": "station_information",
                    "id": "urn:ngsi-ld:station_information:acoruna:ACORUNA-002",
                    "station_id": "ACORUNA-002",
                    "name": "Riazor",
                    "capacity": 25,
                    "location": {
                        "type": "GeoProperty",
                        "value": {"type": "Point", "coordinates": [-8.412, 43.358]},
                    },
                },
            ]
        elif entity_type == "WeatherObserved":
            return [{
                "type": "WeatherObserved",
                "id": "urn:ngsi-ld:WeatherObserved:acoruna:marina-001",
                "windSpeed": 9.6,
                "temperature": 14.8,
                "precipitation": 0.2,
                "weatherType": "cloudy",
            }]
        elif entity_type == "station_status":
            return [{
                "type": "station_status",
                "id": "urn:ngsi-ld:station_status:acoruna:ACORUNA-001",
                "station_id": "ACORUNA-001",
                "num_bikes_available": 8,
                "num_docks_available": 12,
                "is_renting": True,
                "last_reported": "2026-04-22T10:00:00Z",
            }]
        return []
    
    # Mock get_entity for station_status (individual station dynamic data)
    async def mock_get_entity(entity_id: str):
        if "station_status" in entity_id and "ACORUNA-001" in entity_id:
            return {
                "type": "station_status",
                "id": entity_id,
                "num_bikes_available": 8,
                "num_docks_available": 12,
                "is_renting": True,
                "last_reported": "2026-04-22T10:00:00Z",
            }
        elif "station_status" in entity_id:
            # Generic station status for other stations
            return {
                "type": "station_status",
                "id": entity_id,
                "num_bikes_available": 10,
                "num_docks_available": 15,
                "is_renting": True,
                "last_reported": "2026-04-22T10:00:00Z",
            }
        return {}
    
    mock.get_entities = mock_get_entities
    mock.get_entity = mock_get_entity
    
    return mock


@pytest.fixture
def mock_llm():
    """
    Mock LLMClient that returns simple chat responses without tool_calls.
    
    Returns a response dict with a simple non-empty response field.
    """
    mock = AsyncMock()
    
    async def mock_chat(messages: list, tools: list | None = None, **kwargs):
        return {
            "choices": [
                {"message": {"content": "Hay 8 bicis disponibles en María Pita.", "tool_calls": None}}
            ]
        }
    
    mock.chat = mock_chat
    
    return mock


@pytest.fixture
def mock_cratedb():
    """
    Mock CrateDBClient for heatmap data retrieval.
    
    Returns an empty list (no trip data in test environment).
    """
    mock = MagicMock()
    
    def mock_get_trips_heatmap():
        return []
    
    mock.get_trips_heatmap = mock_get_trips_heatmap
    
    return mock


@pytest.fixture
async def client():
    """
    AsyncClient for FastAPI app testing.
    
    Scope: function — each test gets a fresh client instance.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
