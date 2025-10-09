"""Unit tests for HealthMonitor."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from myagent.manager.monitoring.health import HealthMonitor
from myagent.manager.storage.models import (
    HealthStatus,
    ServiceStatus,
)
from tests.manager.fixtures.helpers import MockWebSocketServer


@pytest.mark.unit
class TestHealthMonitor:
    """Test cases for HealthMonitor."""

    # ==================== Health Check Tests ====================

    @pytest.mark.asyncio
    async def test_check_service_health_healthy(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test health check for a healthy service."""
        sample_service.status = ServiceStatus.RUNNING
        health_monitor.repository.save_service(sample_service)

        # Mock successful WebSocket connection
        async with MockWebSocketServer(
            sample_service.host, sample_service.port
        ) as mock_server:
            result = await health_monitor.check_service_health(sample_service)

        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms > 0
        assert "websocket" in result.checks
        assert "status" in result.checks
        assert result.checks["websocket"].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_service_health_unhealthy(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test health check for an unhealthy service."""
        sample_service.status = ServiceStatus.RUNNING
        health_monitor.repository.save_service(sample_service)

        # No WebSocket server running - connection should fail
        result = await health_monitor.check_service_health(sample_service)

        assert result.status == HealthStatus.UNHEALTHY
        assert result.checks["websocket"].status == HealthStatus.UNHEALTHY
        assert result.error_message is None or "connection" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_check_service_health_websocket_timeout(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test health check with WebSocket timeout."""
        sample_service.status = ServiceStatus.RUNNING
        health_monitor.repository.save_service(sample_service)

        # Mock websocket that times out
        with patch("websockets.connect") as mock_connect:
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
            mock_ws.__aexit__ = AsyncMock(return_value=None)
            mock_connect.return_value = mock_ws

            result = await health_monitor.check_service_health(sample_service)

        assert result.checks["websocket"].status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_service_health_stopped_service(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test health check for a stopped service."""
        sample_service.status = ServiceStatus.STOPPED
        health_monitor.repository.save_service(sample_service)

        result = await health_monitor.check_service_health(sample_service)

        assert result.checks["status"].status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_service_health_error_service(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test health check for a service in error state."""
        sample_service.status = ServiceStatus.ERROR
        sample_service.error_message = "Test error"
        health_monitor.repository.save_service(sample_service)

        result = await health_monitor.check_service_health(sample_service)

        assert result.checks["status"].status == HealthStatus.UNHEALTHY
        assert "error" in result.checks["status"].message.lower()

    @pytest.mark.asyncio
    async def test_check_all_services(
        self, health_monitor: HealthMonitor, multiple_services
    ):
        """Test health check for all services."""
        # Save multiple services
        for service in multiple_services:
            service.status = ServiceStatus.RUNNING
            health_monitor.repository.save_service(service)

        results = await health_monitor.check_all_services()

        assert len(results) == len(multiple_services)
        assert all(r.service_id in [s.service_id for s in multiple_services] for r in results)

    @pytest.mark.asyncio
    async def test_check_all_services_with_exception(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test that exceptions in individual checks don't break batch checking."""
        sample_service.status = ServiceStatus.RUNNING
        health_monitor.repository.save_service(sample_service)

        # Mock check_service_health to raise exception
        original_check = health_monitor.check_service_health

        async def mock_check(service):
            if service.service_id == sample_service.service_id:
                raise Exception("Test exception")
            return await original_check(service)

        with patch.object(health_monitor, "check_service_health", side_effect=mock_check):
            results = await health_monitor.check_all_services()

        # Should handle exception gracefully
        assert len(results) == 0  # Failed check doesn't return result

    # ==================== Monitoring Loop Tests ====================

    @pytest.mark.asyncio
    async def test_start_monitoring(self, health_monitor: HealthMonitor):
        """Test starting health monitoring."""
        await health_monitor.start_monitoring(interval=1)

        assert health_monitor._monitoring
        assert health_monitor._monitor_task is not None

        await health_monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, health_monitor: HealthMonitor):
        """Test stopping health monitoring."""
        await health_monitor.start_monitoring(interval=1)
        await asyncio.sleep(0.1)  # Let it run briefly

        await health_monitor.stop_monitoring()

        assert not health_monitor._monitoring
        assert health_monitor._monitor_task.done()

    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(
        self, health_monitor: HealthMonitor
    ):
        """Test starting monitoring when already running."""
        await health_monitor.start_monitoring(interval=1)

        # Try to start again
        await health_monitor.start_monitoring(interval=1)

        assert health_monitor._monitoring

        await health_monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_monitoring_interval(self, health_monitor: HealthMonitor, sample_service):
        """Test that monitoring runs at specified interval."""
        sample_service.status = ServiceStatus.RUNNING
        health_monitor.repository.save_service(sample_service)

        check_count = 0

        original_check = health_monitor.check_all_services

        async def counting_check():
            nonlocal check_count
            check_count += 1
            return await original_check()

        with patch.object(
            health_monitor, "check_all_services", side_effect=counting_check
        ):
            await health_monitor.start_monitoring(interval=0.1)
            await asyncio.sleep(0.35)  # Should trigger ~3 checks
            await health_monitor.stop_monitoring()

        assert check_count >= 2  # At least 2 checks in 0.35s with 0.1s interval

    @pytest.mark.asyncio
    async def test_monitoring_loop_exception_handling(
        self, health_monitor: HealthMonitor
    ):
        """Test that exceptions in monitoring loop don't crash the monitor."""

        async def failing_check():
            raise Exception("Test exception")

        with patch.object(
            health_monitor, "check_all_services", side_effect=failing_check
        ):
            await health_monitor.start_monitoring(interval=0.1)
            await asyncio.sleep(0.25)
            # Should still be running despite exceptions
            assert health_monitor._monitoring

            await health_monitor.stop_monitoring()

    # ==================== Health History Tests ====================

    @pytest.mark.asyncio
    async def test_save_health_check_result(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test saving health check results."""
        sample_service.status = ServiceStatus.RUNNING
        health_monitor.repository.save_service(sample_service)

        # Perform health check (automatically saves)
        result = await health_monitor.check_service_health(sample_service)

        # Verify it was saved
        history = health_monitor.get_service_health_history(
            sample_service.service_id, limit=1
        )

        assert len(history) == 1
        assert history[0].service_id == sample_service.service_id

    @pytest.mark.asyncio
    async def test_get_service_health_history(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test retrieving health check history."""
        sample_service.status = ServiceStatus.RUNNING
        health_monitor.repository.save_service(sample_service)

        # Perform multiple health checks
        for _ in range(5):
            await health_monitor.check_service_health(sample_service)
            await asyncio.sleep(0.01)  # Small delay to ensure different timestamps

        # Get history with limit
        history = health_monitor.get_service_health_history(
            sample_service.service_id, limit=3
        )

        assert len(history) <= 3
        # Should be in reverse chronological order
        if len(history) > 1:
            assert history[0].timestamp >= history[1].timestamp

    @pytest.mark.asyncio
    async def test_get_health_summary(
        self, health_monitor: HealthMonitor, multiple_services
    ):
        """Test getting overall health summary."""
        # Setup services with different statuses
        multiple_services[0].status = ServiceStatus.RUNNING
        multiple_services[1].status = ServiceStatus.UNHEALTHY
        multiple_services[2].status = ServiceStatus.STOPPED

        for service in multiple_services:
            health_monitor.repository.save_service(service)

        summary = health_monitor.get_health_summary()

        assert summary["total"] == 3
        assert summary["healthy"] == 1
        assert summary["unhealthy"] == 1
        assert summary["unknown"] == 1

    # ==================== Status Update Tests ====================

    @pytest.mark.asyncio
    async def test_unhealthy_status_update(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test that unhealthy check updates service status."""
        sample_service.status = ServiceStatus.RUNNING
        health_monitor.repository.save_service(sample_service)

        # Health check will fail (no WebSocket server)
        result = await health_monitor.check_service_health(sample_service)

        # Verify status was updated to UNHEALTHY
        updated_service = health_monitor.repository.get_service(sample_service.service_id)
        assert updated_service.status == ServiceStatus.UNHEALTHY
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_healthy_status_recovery(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test that healthy check recovers service from UNHEALTHY."""
        sample_service.status = ServiceStatus.UNHEALTHY
        sample_service.error_message = "Previous error"
        health_monitor.repository.save_service(sample_service)

        # Mock successful health check
        async with MockWebSocketServer(sample_service.host, sample_service.port):
            result = await health_monitor.check_service_health(sample_service)

        # Verify status recovered to RUNNING
        updated_service = health_monitor.repository.get_service(sample_service.service_id)
        assert updated_service.status == ServiceStatus.RUNNING
        assert updated_service.error_message is None
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_last_health_check_timestamp(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test that last health check timestamp is updated."""
        sample_service.status = ServiceStatus.RUNNING
        sample_service.last_health_check = None
        health_monitor.repository.save_service(sample_service)

        await health_monitor.check_service_health(sample_service)

        updated_service = health_monitor.repository.get_service(sample_service.service_id)
        assert updated_service.last_health_check is not None
        assert isinstance(updated_service.last_health_check, datetime)

    # ==================== WebSocket Check Tests ====================

    @pytest.mark.asyncio
    async def test_websocket_check_with_response(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test WebSocket check receives and validates response."""
        sample_service.status = ServiceStatus.RUNNING

        async with MockWebSocketServer(sample_service.host, sample_service.port) as server:
            result = await health_monitor._check_websocket_connectivity(sample_service)

        assert result.status == HealthStatus.HEALTHY
        assert result.duration_ms > 0
        assert len(server.messages_received) > 0  # Ping was received

    @pytest.mark.asyncio
    async def test_websocket_check_connection_refused(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test WebSocket check handles connection refused."""
        sample_service.status = ServiceStatus.RUNNING

        result = await health_monitor._check_websocket_connectivity(sample_service)

        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.message.lower() or "connection" in result.message.lower()

    # ==================== Service Status Check Tests ====================

    def test_service_status_check_running(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test status check for running service."""
        sample_service.status = ServiceStatus.RUNNING

        result = health_monitor._check_service_status(sample_service)

        assert result.status == HealthStatus.HEALTHY
        assert "running" in result.message.lower()

    def test_service_status_check_error(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test status check for service in error state."""
        sample_service.status = ServiceStatus.ERROR
        sample_service.error_message = "Process crashed"

        result = health_monitor._check_service_status(sample_service)

        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.message.lower()
        assert "crashed" in result.message.lower()

    def test_service_status_check_stopped(
        self, health_monitor: HealthMonitor, sample_service
    ):
        """Test status check for stopped service."""
        sample_service.status = ServiceStatus.STOPPED

        result = health_monitor._check_service_status(sample_service)

        assert result.status == HealthStatus.UNHEALTHY
        assert "not running" in result.message.lower()
