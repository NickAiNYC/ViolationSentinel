"""
API Integration Tests
Test FastAPI endpoints
"""

import pytest
from httpx import AsyncClient
from backend.api.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test basic health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "ViolationSentinel"


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "docs" in data


@pytest.mark.asyncio
async def test_liveness_probe():
    """Test liveness probe"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/liveness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
