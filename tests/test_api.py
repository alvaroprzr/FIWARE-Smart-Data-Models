"""
Test suite for BiciCoruña Smart backend API endpoints.

Tests all 7 API endpoints with mocked Orion, LLM, and CrateDB clients:
1. Health check
2. Get stations list
3. Get station status
4. Get demand forecast
5. Chat endpoint
6. Current weather
7. Trip heatmap
"""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient


class TestHealth:
    """Test /health endpoint."""
    
    async def test_health(self, client: AsyncClient):
        """
        GET /health should return 200 with status='ok'.
        """
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestStations:
    """Test /api/stations endpoints."""
    
    async def test_get_stations(self, client: AsyncClient, mock_orion):
        """
        GET /api/stations?city=acoruna should return 200 with items list.
        
        Response structure:
        - items: list with at least 1 station
        - Each station has: station_id, name
        """
        with patch("backend.routers.stations.OrionClient") as mock_orion_cls:
            mock_orion_cls.return_value = mock_orion
            
            response = await client.get("/api/stations?city=acoruna")
            assert response.status_code == 200
            
            data = response.json()
            assert "items" in data
            assert isinstance(data["items"], list)
            assert len(data["items"]) >= 1
            
            # Verify first station structure
            first_station = data["items"][0]
            assert "station_id" in first_station
            assert "name" in first_station
    
    async def test_get_station_status(self, client: AsyncClient, mock_orion):
        """
        GET /api/stations/{station_id}/status should return 200 with status fields.
        
        Response must include:
        - num_bikes_available: int
        - last_reported: str (ISO timestamp)
        """
        with patch("backend.routers.stations.OrionClient") as mock_orion_cls:
            mock_orion_cls.return_value = mock_orion
            
            response = await client.get("/api/stations/ACORUNA-001/status")
            assert response.status_code == 200
            
            data = response.json()
            assert "num_bikes_available" in data
            assert isinstance(data["num_bikes_available"], int)
            assert "last_reported" in data
            assert isinstance(data["last_reported"], str)
    
    async def test_get_forecast(self, client: AsyncClient, mock_orion):
        """
        GET /api/stations/{station_id}/forecast should return 200 with forecast data.
        
        Response must include:
        - t30: dict with value (float, 0-25 range)
        - t60: dict with value (float, 0-25 range)
        """
        with patch("backend.routers.stations.OrionClient") as mock_orion_cls:
            mock_orion_cls.return_value = mock_orion
            # Mock the predict function since forecast calls ML predictor
            with patch("backend.routers.stations.predict") as mock_predict:
                mock_predict.return_value = {
                    "t30": {"value": 8.5, "low": 6.0, "high": 11.0},
                    "t60": {"value": 12.3, "low": 9.0, "high": 15.0},
                    "model_used": "fallback"
                }
                
                response = await client.get("/api/stations/ACORUNA-001/forecast")
                assert response.status_code == 200
                
                data = response.json()
                assert "t30" in data
                assert "t60" in data
                
                # Verify structure and value ranges
                assert "value" in data["t30"]
                assert "value" in data["t60"]
                assert isinstance(data["t30"]["value"], (int, float))
                assert isinstance(data["t60"]["value"], (int, float))
                assert 0 <= data["t30"]["value"] <= 25
                assert 0 <= data["t60"]["value"] <= 25


class TestChat:
    """Test /api/chat endpoint."""
    
    async def test_chat(self, client: AsyncClient, mock_orion, mock_llm):
        """
        POST /api/chat should return 200 with chat response.
        
        Request body: {"city": "acoruna", "message": "¿Bicis en María Pita?"}
        Response must include:
        - response: non-empty string
        """
        with patch("backend.routers.chat.OrionClient") as mock_orion_cls, \
             patch("backend.routers.chat.LLMClient") as mock_llm_cls:
            mock_orion_cls.return_value = mock_orion
            mock_llm_cls.return_value = mock_llm
            
            payload = {
                "city": "acoruna",
                "message": "¿Bicis en María Pita?",
            }
            response = await client.post("/api/chat", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            assert "response" in data
            assert isinstance(data["response"], str)
            assert len(data["response"]) > 0


class TestWeather:
    """Test /api/weather endpoints."""
    
    async def test_weather(self, client: AsyncClient, mock_orion):
        """
        GET /api/weather?city=acoruna should return 200 with weather fields.
        
        Response must include:
        - windSpeed: float
        - temperature: float
        """
        with patch("backend.routers.weather.OrionClient") as mock_orion_cls:
            mock_orion_cls.return_value = mock_orion
            
            response = await client.get("/api/weather?city=acoruna")
            assert response.status_code == 200
            
            data = response.json()
            assert "windSpeed" in data
            assert "temperature" in data
            assert isinstance(data["windSpeed"], (int, float))
            assert isinstance(data["temperature"], (int, float))
    
    async def test_heatmap(self, client: AsyncClient, mock_orion, mock_cratedb):
        """
        GET /api/weather/trips/heatmap?city=acoruna should return 200 with list.
        
        Response is a list (can be empty in test environment).
        All external services (Orion, CrateDB) are mocked for isolation.
        """
        with patch("backend.routers.weather.OrionClient") as mock_orion_cls, \
             patch("backend.routers.weather.CrateDBClient") as mock_cratedb_cls:
            mock_orion_cls.return_value = mock_orion
            mock_cratedb_cls.return_value = mock_cratedb
            
            response = await client.get("/api/weather/trips/heatmap?city=acoruna")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
