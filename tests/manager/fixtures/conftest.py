"""Manager-specific test fixtures."""

import asyncio
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from myagent.manager.core.manager import AgentManager
from myagent.manager.core.registry import ServiceRegistry
from myagent.manager.core.router import ConnectionRouter
from myagent.manager.monitoring.health import HealthMonitor
from myagent.manager.storage.models import (
    AgentService,
    ServiceConfig,
    ServiceStatus,
    RoutingStrategy,
)
from myagent.manager.storage.repository import ServiceRepository


@pytest.fixture
async def repository(temp_db_path: Path) -> ServiceRepository:
    """Create a test service repository."""
    repo = ServiceRepository(str(temp_db_path))
    return repo


@pytest.fixture
async def service_registry(repository: ServiceRepository) -> ServiceRegistry:
    """Create a test service registry."""
    return ServiceRegistry(repository)


@pytest.fixture
async def connection_router(repository: ServiceRepository) -> ConnectionRouter:
    """Create a test connection router."""
    return ConnectionRouter(repository)


@pytest.fixture
async def health_monitor(repository: ServiceRepository) -> HealthMonitor:
    """Create a test health monitor."""
    return HealthMonitor(repository)


@pytest.fixture
async def agent_manager(temp_db_path: Path) -> AsyncGenerator[AgentManager, None]:
    """Create a test agent manager."""
    manager = AgentManager(str(temp_db_path))
    yield manager
    # Cleanup
    if manager._running:
        await manager.stop()


@pytest.fixture
def service_config(sample_agent_file: Path) -> ServiceConfig:
    """Create a test service configuration."""
    return ServiceConfig(
        agent_factory_path=str(sample_agent_file),
        max_sessions=10,
        session_timeout=300,
        auto_restart=True,
        max_restart_count=3,
        restart_delay=5,
        health_check_enabled=True,
        health_check_interval=10,
        environment={},
    )


@pytest.fixture
def sample_service(service_config: ServiceConfig) -> AgentService:
    """Create a sample agent service for testing."""
    return AgentService(
        name="test_service",
        description="Test service for unit tests",
        host="localhost",
        port=8888,
        endpoint="ws://localhost:8888",
        tags={"test", "sample"},
        config=service_config,
        status=ServiceStatus.STOPPED,
    )


@pytest.fixture
def multiple_services(service_config: ServiceConfig) -> list[AgentService]:
    """Create multiple sample services for testing."""
    services = []
    for i in range(3):
        service = AgentService(
            name=f"test_service_{i}",
            description=f"Test service {i}",
            host="localhost",
            port=8888 + i,
            endpoint=f"ws://localhost:{8888 + i}",
            tags={f"service_{i}", "test"},
            config=service_config,
            status=ServiceStatus.STOPPED,
        )
        services.append(service)
    return services


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    mock_ws = AsyncMock()
    mock_ws.remote_address = ("127.0.0.1", 54321)
    mock_ws.path = "/"
    mock_ws.request_headers = {"user-agent": "test-client"}
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock()
    mock_ws.close = AsyncMock()
    return mock_ws


@pytest.fixture
def mock_process():
    """Create a mock subprocess.Popen for testing."""
    mock_proc = MagicMock()
    mock_proc.poll = MagicMock(return_value=None)  # Running
    mock_proc.terminate = MagicMock()
    mock_proc.kill = MagicMock()
    mock_proc.communicate = MagicMock(return_value=("", ""))
    return mock_proc
