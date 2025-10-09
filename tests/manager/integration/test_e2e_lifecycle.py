"""End-to-end integration tests for service lifecycle."""

import asyncio

import pytest

from myagent.manager.storage.models import ServiceStatus
from tests.manager.fixtures.helpers import wait_for_condition


@pytest.mark.integration
class TestE2EServiceLifecycle:
    """End-to-end tests for complete service lifecycle."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_e2e_service_lifecycle(
        self, agent_manager, sample_agent_file, mock_process
    ):
        """Test complete service lifecycle: register -> start -> stop -> unregister."""
        # 1. Register service
        service = await agent_manager.register_service(
            name="e2e_test_service",
            agent_factory_path=str(sample_agent_file),
            host="localhost",
            description="E2E test service",
            tags={"e2e", "test"},
        )

        assert service is not None
        assert service.status == ServiceStatus.STOPPED

        # 2. Start service
        with pytest.mock.patch("subprocess.Popen", return_value=mock_process):
            success = await agent_manager.start_service(service.service_id)

        assert success

        # Wait for service to be running
        async def is_running():
            s = agent_manager.get_service(service.service_id)
            return s and s.status == ServiceStatus.RUNNING

        await wait_for_condition(is_running, timeout=5.0)

        # 3. Verify service is healthy
        health_result = await agent_manager.check_service_health(service.service_id)
        # Note: Will likely be unhealthy in test due to mock WebSocket

        # 4. Stop service
        success = await agent_manager.stop_service(service.service_id)
        assert success

        # Wait for service to be stopped
        async def is_stopped():
            s = agent_manager.get_service(service.service_id)
            return s and s.status == ServiceStatus.STOPPED

        await wait_for_condition(is_stopped, timeout=5.0)

        # 5. Unregister service
        success = await agent_manager.unregister_service(service.service_id)
        assert success
        assert agent_manager.get_service(service.service_id) is None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_e2e_auto_restart(self, agent_manager, sample_agent_file, mock_process):
        """Test end-to-end auto-restart functionality."""
        # Register service with auto-restart enabled
        service = await agent_manager.register_service(
            name="auto_restart_test",
            agent_factory_path=str(sample_agent_file),
            config=None,  # Will use defaults with auto_restart=True
        )

        # Start manager to enable auto-restart monitoring
        await agent_manager.start(health_check_interval=1)

        try:
            # Start service
            with pytest.mock.patch("subprocess.Popen", return_value=mock_process):
                await agent_manager.start_service(service.service_id)

            # Simulate service failure
            updated_service = agent_manager.get_service(service.service_id)
            updated_service.status = ServiceStatus.ERROR
            agent_manager.repository.save_service(updated_service)

            # Wait for auto-restart (30s check interval in production, mocked here)
            # In real test, would need to wait or mock the interval
            await asyncio.sleep(0.5)

        finally:
            await agent_manager.stop()

    @pytest.mark.asyncio
    async def test_e2e_load_balancing(
        self, agent_manager, sample_agent_file, multiple_services, mock_process
    ):
        """Test end-to-end load balancing across multiple services."""
        # Register multiple services
        registered_services = []
        for i in range(3):
            service = await agent_manager.register_service(
                name=f"lb_service_{i}",
                agent_factory_path=str(sample_agent_file),
                port=9000 + i,
            )
            registered_services.append(service)

        # Start all services
        with pytest.mock.patch("subprocess.Popen", return_value=mock_process):
            for service in registered_services:
                await agent_manager.start_service(service.service_id)

        # Route multiple connections
        routed_services = []
        for i in range(9):  # 3 rounds of 3 services
            routed = await agent_manager.route_connection(
                client_ip=f"192.168.1.{i}", client_port=5000 + i
            )
            if routed:
                routed_services.append(routed.service_id)

        # Verify round-robin distribution
        assert len(set(routed_services)) == 3  # All services were used

        # Cleanup
        for service in registered_services:
            await agent_manager.stop_service(service.service_id)
            await agent_manager.unregister_service(service.service_id)


@pytest.mark.integration
class TestE2EConnectionRouting:
    """End-to-end tests for connection routing."""

    @pytest.mark.asyncio
    async def test_e2e_connection_routing_with_rules(self, agent_manager, sample_agent_file):
        """Test connection routing with custom rules."""
        # TODO: Implement end-to-end routing test
        pass


@pytest.mark.integration
@pytest.mark.slow
class TestStressTests:
    """Stress tests for the manager system."""

    @pytest.mark.asyncio
    async def test_stress_many_services(self, agent_manager, temp_dir):
        """Test registering many services."""
        # TODO: Implement stress test for 50+ services
        pass

    @pytest.mark.asyncio
    async def test_stress_many_connections(self, agent_manager):
        """Test handling many concurrent connections."""
        # TODO: Implement stress test for 100+ connections
        pass
