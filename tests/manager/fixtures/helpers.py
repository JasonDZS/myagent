"""Test helper utilities for Manager tests."""

import asyncio
import socket
from pathlib import Path
from typing import Optional

from myagent.manager.storage.models import (
    AgentService,
    ServiceConfig,
    ServiceStatus,
)


def find_free_port(start_port: int = 9000, end_port: int = 9100) -> Optional[int]:
    """Find a free port in the given range."""
    for port in range(start_port, end_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("localhost", port))
                return port
        except OSError:
            continue
    return None


def create_test_agent_file(path: Path, agent_name: str = "test_agent") -> Path:
    """Create a test agent factory file."""
    agent_file = path / f"{agent_name}.py"
    agent_file.write_text(f'''"""Test agent factory for {agent_name}."""
from myagent import create_react_agent

def create_agent():
    """Create a test agent."""
    return create_react_agent(
        [],
        llm_config={{
            "model": "gpt-4",
            "api_key": "test-key-{agent_name}",
        }}
    )
''')
    return agent_file


async def wait_for_condition(
    condition_func,
    timeout: float = 5.0,
    interval: float = 0.1,
    error_message: str = "Condition not met within timeout",
):
    """Wait for a condition to become true."""
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
            return True
        await asyncio.sleep(interval)
    raise TimeoutError(error_message)


def assert_service_equals(actual: AgentService, expected: AgentService, ignore_fields: Optional[list[str]] = None):
    """Assert two services are equal, optionally ignoring certain fields."""
    ignore_fields = ignore_fields or []

    fields_to_check = [
        "name", "description", "host", "port", "endpoint",
        "tags", "status", "service_id"
    ]

    for field in fields_to_check:
        if field not in ignore_fields:
            assert getattr(actual, field) == getattr(expected, field), \
                f"Field '{field}' mismatch: {getattr(actual, field)} != {getattr(expected, field)}"


class MockWebSocketServer:
    """Mock WebSocket server for testing."""

    def __init__(self, host: str = "localhost", port: int = 8888):
        self.host = host
        self.port = port
        self.server = None
        self.connections = []
        self.messages_received = []

    async def start(self):
        """Start the mock server."""
        import websockets

        async def handler(websocket):
            self.connections.append(websocket)
            try:
                async for message in websocket:
                    self.messages_received.append(message)
                    # Echo back
                    await websocket.send(message)
            except Exception:
                pass
            finally:
                if websocket in self.connections:
                    self.connections.remove(websocket)

        self.server = await websockets.serve(handler, self.host, self.port)

    async def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


class ServiceBuilder:
    """Builder pattern for creating test services."""

    def __init__(self):
        self._name = "test_service"
        self._description = "Test service"
        self._host = "localhost"
        self._port = 8888
        self._tags = set()
        self._status = ServiceStatus.STOPPED
        self._config = None

    def with_name(self, name: str) -> "ServiceBuilder":
        self._name = name
        return self

    def with_description(self, description: str) -> "ServiceBuilder":
        self._description = description
        return self

    def with_host(self, host: str) -> "ServiceBuilder":
        self._host = host
        return self

    def with_port(self, port: int) -> "ServiceBuilder":
        self._port = port
        return self

    def with_tags(self, *tags: str) -> "ServiceBuilder":
        self._tags = set(tags)
        return self

    def with_status(self, status: ServiceStatus) -> "ServiceBuilder":
        self._status = status
        return self

    def with_config(self, config: ServiceConfig) -> "ServiceBuilder":
        self._config = config
        return self

    def build(self) -> AgentService:
        """Build the service."""
        if self._config is None:
            self._config = ServiceConfig(
                agent_factory_path="/tmp/test_agent.py",
            )

        return AgentService(
            name=self._name,
            description=self._description,
            host=self._host,
            port=self._port,
            endpoint=f"ws://{self._host}:{self._port}",
            tags=self._tags,
            config=self._config,
            status=self._status,
        )
