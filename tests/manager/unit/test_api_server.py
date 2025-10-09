"""Unit tests for APIServer.

NOTE: These are template tests. Full implementation requires httpx/TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from myagent.manager.api.server import APIServer
from myagent.manager.core.manager import AgentManager


@pytest.mark.unit
class TestAPIServer:
    """Test cases for APIServer."""

    @pytest.fixture
    def api_client(self, agent_manager: AgentManager):
        """Create FastAPI test client."""
        api_server = APIServer(agent_manager)
        return TestClient(api_server.app)

    # ==================== Service Management Tests ====================

    @pytest.mark.asyncio
    async def test_api_create_service(self, api_client, sample_agent_file):
        """Test POST /api/v1/services."""
        response = api_client.post(
            "/api/v1/services",
            json={
                "name": "test_service",
                "agent_factory_path": str(sample_agent_file),
                "host": "localhost",
                "port": 8888,
                "description": "Test service",
                "tags": ["test"],
                "auto_start": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_service"
        assert data["port"] == 8888

    @pytest.mark.asyncio
    async def test_api_list_services(self, api_client):
        """Test GET /api/v1/services."""
        response = api_client.get("/api/v1/services")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_api_get_service(self, api_client):
        """Test GET /api/v1/services/{id}."""
        # TODO: Create service first, then get it
        pass

    @pytest.mark.asyncio
    async def test_api_update_service(self, api_client):
        """Test PUT /api/v1/services/{id}."""
        # TODO: Create service, then update it
        pass

    @pytest.mark.asyncio
    async def test_api_delete_service(self, api_client):
        """Test DELETE /api/v1/services/{id}."""
        # TODO: Create service, then delete it
        pass

    # ==================== Service Control Tests ====================

    @pytest.mark.asyncio
    async def test_api_start_service(self, api_client):
        """Test POST /api/v1/services/{id}/start."""
        # TODO: Implement test
        pass

    @pytest.mark.asyncio
    async def test_api_stop_service(self, api_client):
        """Test POST /api/v1/services/{id}/stop."""
        # TODO: Implement test
        pass

    @pytest.mark.asyncio
    async def test_api_restart_service(self, api_client):
        """Test POST /api/v1/services/{id}/restart."""
        # TODO: Implement test
        pass

    # ==================== Health & Stats Tests ====================

    @pytest.mark.asyncio
    async def test_api_health_check(self, api_client):
        """Test GET /health."""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_api_get_system_stats(self, api_client):
        """Test GET /api/v1/stats."""
        response = api_client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "connections" in data

    # ==================== Error Handling Tests ====================

    @pytest.mark.asyncio
    async def test_api_not_found(self, api_client):
        """Test 404 for nonexistent service."""
        response = api_client.get("/api/v1/services/nonexistent_id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_api_bad_request(self, api_client):
        """Test 400 for invalid request."""
        response = api_client.post("/api/v1/services", json={"invalid": "data"})

        assert response.status_code in [400, 422]  # 422 for validation errors
