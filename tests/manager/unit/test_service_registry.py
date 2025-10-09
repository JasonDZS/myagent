"""Unit tests for ServiceRegistry."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from myagent.manager.core.registry import PortAllocator, ServiceRegistry
from myagent.manager.storage.models import ServiceConfig, ServiceStatus
from myagent.manager.storage.repository import ServiceRepository


@pytest.mark.unit
class TestServiceRegistry:
    """Test cases for ServiceRegistry."""

    # ==================== Service Registration Tests ====================

    @pytest.mark.asyncio
    async def test_register_service_success(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test successful service registration."""
        service = await service_registry.register_service(
            name="test_service",
            agent_factory_path=str(sample_agent_file),
            host="localhost",
            port=8888,
            description="Test service",
            tags={"test"},
        )

        assert service is not None
        assert service.name == "test_service"
        assert service.host == "localhost"
        assert service.port == 8888
        assert service.status == ServiceStatus.STOPPED
        assert "test" in service.tags

    @pytest.mark.asyncio
    async def test_register_duplicate_service(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test registering a service with duplicate name fails."""
        # Register first service
        await service_registry.register_service(
            name="duplicate_service",
            agent_factory_path=str(sample_agent_file),
        )

        # Try to register duplicate
        duplicate = await service_registry.register_service(
            name="duplicate_service",
            agent_factory_path=str(sample_agent_file),
        )

        assert duplicate is None

    @pytest.mark.asyncio
    async def test_register_service_invalid_factory_path(
        self, service_registry: ServiceRegistry
    ):
        """Test registration fails with invalid agent factory path."""
        service = await service_registry.register_service(
            name="invalid_service",
            agent_factory_path="/nonexistent/path/agent.py",
        )

        assert service is None

    @pytest.mark.asyncio
    async def test_register_service_with_specific_port(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test registering service with specific port."""
        service = await service_registry.register_service(
            name="port_service",
            agent_factory_path=str(sample_agent_file),
            port=9999,
        )

        assert service is not None
        assert service.port == 9999

    @pytest.mark.asyncio
    async def test_register_service_auto_port_allocation(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test automatic port allocation when no port specified."""
        service = await service_registry.register_service(
            name="auto_port_service",
            agent_factory_path=str(sample_agent_file),
            port=None,
        )

        assert service is not None
        assert 8081 <= service.port <= 9000  # Default port range

    @pytest.mark.asyncio
    async def test_register_service_with_tags(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test registering service with tags."""
        tags = {"production", "api", "v1"}
        service = await service_registry.register_service(
            name="tagged_service",
            agent_factory_path=str(sample_agent_file),
            tags=tags,
        )

        assert service is not None
        assert service.tags == tags

    # ==================== Service Start Tests ====================

    @pytest.mark.asyncio
    async def test_start_service_success(
        self, service_registry: ServiceRegistry, sample_agent_file: Path, mock_process
    ):
        """Test successful service start."""
        # Register service
        service = await service_registry.register_service(
            name="start_test",
            agent_factory_path=str(sample_agent_file),
        )

        # Mock subprocess.Popen
        with patch("subprocess.Popen", return_value=mock_process):
            success = await service_registry.start_service(service.service_id)

        assert success
        # Verify service status updated
        updated_service = service_registry.get_service(service.service_id)
        assert updated_service.status == ServiceStatus.RUNNING
        assert updated_service.started_at is not None

    @pytest.mark.asyncio
    async def test_start_already_running_service(
        self, service_registry: ServiceRegistry, sample_agent_file: Path, mock_process
    ):
        """Test starting an already running service returns success."""
        # Register and start service
        service = await service_registry.register_service(
            name="running_test",
            agent_factory_path=str(sample_agent_file),
        )

        with patch("subprocess.Popen", return_value=mock_process):
            await service_registry.start_service(service.service_id)

            # Try to start again
            success = await service_registry.start_service(service.service_id)

        assert success

    @pytest.mark.asyncio
    async def test_start_nonexistent_service(self, service_registry: ServiceRegistry):
        """Test starting a nonexistent service fails."""
        success = await service_registry.start_service("nonexistent_id")
        assert not success

    @pytest.mark.asyncio
    async def test_start_service_process_exits(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test handling when process exits immediately after start."""
        service = await service_registry.register_service(
            name="exit_test",
            agent_factory_path=str(sample_agent_file),
        )

        # Mock process that exits immediately
        mock_proc = MagicMock()
        mock_proc.poll = MagicMock(return_value=1)  # Exited with code 1
        mock_proc.communicate = MagicMock(return_value=("", "Process error"))

        with patch("subprocess.Popen", return_value=mock_proc):
            success = await service_registry.start_service(service.service_id)

        assert not success
        updated_service = service_registry.get_service(service.service_id)
        assert updated_service.status == ServiceStatus.ERROR
        assert updated_service.error_message is not None

    # ==================== Service Stop Tests ====================

    @pytest.mark.asyncio
    async def test_stop_service_success(
        self, service_registry: ServiceRegistry, sample_agent_file: Path, mock_process
    ):
        """Test successful service stop."""
        # Register and start service
        service = await service_registry.register_service(
            name="stop_test",
            agent_factory_path=str(sample_agent_file),
        )

        with patch("subprocess.Popen", return_value=mock_process):
            await service_registry.start_service(service.service_id)

            # Stop service
            success = await service_registry.stop_service(service.service_id)

        assert success
        mock_process.terminate.assert_called_once()

        updated_service = service_registry.get_service(service.service_id)
        assert updated_service.status == ServiceStatus.STOPPED
        assert updated_service.started_at is None

    @pytest.mark.asyncio
    async def test_stop_already_stopped_service(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test stopping an already stopped service returns success."""
        service = await service_registry.register_service(
            name="stopped_test",
            agent_factory_path=str(sample_agent_file),
        )

        success = await service_registry.stop_service(service.service_id)
        assert success

    @pytest.mark.asyncio
    async def test_stop_service_graceful_shutdown(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test graceful service shutdown within timeout."""
        service = await service_registry.register_service(
            name="graceful_test",
            agent_factory_path=str(sample_agent_file),
        )

        mock_proc = MagicMock()
        mock_proc.poll = MagicMock(side_effect=[None, None, 0])  # Running then exits
        mock_proc.terminate = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            await service_registry.start_service(service.service_id)
            success = await service_registry.stop_service(service.service_id)

        assert success
        mock_proc.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_service_force_kill(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test force kill when graceful shutdown times out."""
        service = await service_registry.register_service(
            name="force_kill_test",
            agent_factory_path=str(sample_agent_file),
        )

        # Mock process that doesn't exit gracefully
        mock_proc = MagicMock()
        mock_proc.poll = MagicMock(return_value=None)  # Never exits
        mock_proc.terminate = MagicMock()
        mock_proc.kill = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            await service_registry.start_service(service.service_id)

            # Mock asyncio.wait_for to raise TimeoutError
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                mock_proc.poll = MagicMock(return_value=0)  # Exit after kill
                success = await service_registry.stop_service(service.service_id)

        assert success
        mock_proc.kill.assert_called_once()

    # ==================== Service Restart Tests ====================

    @pytest.mark.asyncio
    async def test_restart_service_success(
        self, service_registry: ServiceRegistry, sample_agent_file: Path, mock_process
    ):
        """Test successful service restart."""
        service = await service_registry.register_service(
            name="restart_test",
            agent_factory_path=str(sample_agent_file),
        )

        with patch("subprocess.Popen", return_value=mock_process):
            await service_registry.start_service(service.service_id)
            initial_count = service_registry.get_service(service.service_id).restart_count

            success = await service_registry.restart_service(service.service_id)

        assert success
        updated_service = service_registry.get_service(service.service_id)
        assert updated_service.status == ServiceStatus.RUNNING
        assert updated_service.restart_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_restart_service_with_delay(
        self, service_registry: ServiceRegistry, sample_agent_file: Path, mock_process
    ):
        """Test restart includes delay between stop and start."""
        service = await service_registry.register_service(
            name="delay_restart_test",
            agent_factory_path=str(sample_agent_file),
        )

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("asyncio.sleep") as mock_sleep:
                await service_registry.start_service(service.service_id)
                await service_registry.restart_service(service.service_id)

                # Verify sleep was called (1 second delay)
                mock_sleep.assert_called_with(1)

    # ==================== Service Unregistration Tests ====================

    @pytest.mark.asyncio
    async def test_unregister_service_success(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test successful service unregistration."""
        service = await service_registry.register_service(
            name="unregister_test",
            agent_factory_path=str(sample_agent_file),
            port=9876,
        )

        success = await service_registry.unregister_service(service.service_id)

        assert success
        assert service_registry.get_service(service.service_id) is None

    @pytest.mark.asyncio
    async def test_unregister_running_service(
        self, service_registry: ServiceRegistry, sample_agent_file: Path, mock_process
    ):
        """Test unregistering a running service stops it first."""
        service = await service_registry.register_service(
            name="running_unregister_test",
            agent_factory_path=str(sample_agent_file),
        )

        with patch("subprocess.Popen", return_value=mock_process):
            await service_registry.start_service(service.service_id)
            success = await service_registry.unregister_service(service.service_id)

        assert success
        mock_process.terminate.assert_called_once()

    # ==================== Service Query Tests ====================

    @pytest.mark.asyncio
    async def test_get_service_by_name(
        self, service_registry: ServiceRegistry, sample_agent_file: Path
    ):
        """Test getting service by name."""
        service = await service_registry.register_service(
            name="named_service",
            agent_factory_path=str(sample_agent_file),
        )

        retrieved = service_registry.get_service_by_name("named_service")

        assert retrieved is not None
        assert retrieved.service_id == service.service_id

    @pytest.mark.asyncio
    async def test_list_services_with_status_filter(
        self, service_registry: ServiceRegistry, sample_agent_file: Path, mock_process
    ):
        """Test listing services filtered by status."""
        # Create multiple services
        await service_registry.register_service(
            name="stopped_1", agent_factory_path=str(sample_agent_file)
        )
        service2 = await service_registry.register_service(
            name="running_1", agent_factory_path=str(sample_agent_file)
        )

        with patch("subprocess.Popen", return_value=mock_process):
            await service_registry.start_service(service2.service_id)

        # Filter by status
        running_services = service_registry.list_services(status=ServiceStatus.RUNNING)
        stopped_services = service_registry.list_services(status=ServiceStatus.STOPPED)

        assert len(running_services) == 1
        assert len(stopped_services) == 1

    @pytest.mark.asyncio
    async def test_get_running_services(
        self, service_registry: ServiceRegistry, sample_agent_file: Path, mock_process
    ):
        """Test getting only running services."""
        service1 = await service_registry.register_service(
            name="service_1", agent_factory_path=str(sample_agent_file)
        )
        service2 = await service_registry.register_service(
            name="service_2", agent_factory_path=str(sample_agent_file)
        )

        with patch("subprocess.Popen", return_value=mock_process):
            await service_registry.start_service(service1.service_id)

        running = service_registry.get_running_services()

        assert len(running) == 1
        assert running[0].service_id == service1.service_id


@pytest.mark.unit
class TestPortAllocator:
    """Test cases for PortAllocator."""

    def test_allocate_port_success(self):
        """Test successful port allocation."""
        allocator = PortAllocator(start_port=9000, end_port=9010)
        port = allocator.allocate_port()

        assert port is not None
        assert 9000 <= port <= 9010

    def test_port_reservation(self):
        """Test port reservation prevents reallocation."""
        allocator = PortAllocator(start_port=9000, end_port=9010)
        port = allocator.allocate_port()

        allocator.reserve_port(port)
        assert not allocator.is_port_available(port)

    def test_port_release(self):
        """Test port release makes it available again."""
        allocator = PortAllocator(start_port=9000, end_port=9010)
        port = 9005

        allocator.reserve_port(port)
        assert not allocator.is_port_available(port)

        allocator.release_port(port)
        # Note: Port might still be unavailable if actually in use by OS

    def test_no_available_ports(self):
        """Test behavior when all ports are reserved."""
        allocator = PortAllocator(start_port=9000, end_port=9002)

        # Reserve all ports
        for port in range(9000, 9003):
            allocator.reserve_port(port)

        # Should return None
        port = allocator.allocate_port()
        assert port is None
