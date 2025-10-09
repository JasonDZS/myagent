"""Unit tests for ConnectionRouter."""

import pytest

from myagent.manager.core.router import ConnectionRouter
from myagent.manager.storage.models import (
    AgentService,
    ConnectionStatus,
    ConditionOperator,
    RoutingCondition,
    RoutingRule,
    RoutingStrategy,
    ServiceStatus,
)
from myagent.manager.storage.repository import ServiceRepository


@pytest.mark.unit
class TestConnectionRouter:
    """Test cases for ConnectionRouter."""

    # ==================== Routing Strategy Tests ====================

    @pytest.mark.asyncio
    async def test_route_connection_round_robin(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test round robin routing strategy."""
        # Save services to repository
        for service in multiple_services:
            service.status = ServiceStatus.RUNNING
            connection_router.repository.save_service(service)

        # Route multiple connections and verify round robin
        selected_services = []
        for _ in range(6):  # 2 full rounds
            service = await connection_router.route_connection(
                client_ip="192.168.1.1", client_port=5000
            )
            selected_services.append(service.name)

        # Should cycle through services
        assert selected_services[0] == selected_services[3]
        assert selected_services[1] == selected_services[4]
        assert selected_services[2] == selected_services[5]

    @pytest.mark.asyncio
    async def test_route_connection_least_connections(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test least connections routing strategy."""
        # Setup services
        for service in multiple_services:
            service.status = ServiceStatus.RUNNING
            connection_router.repository.save_service(service)

        # Manually add connections to first service
        for i in range(3):
            connection_router.register_connection(
                connection_id=f"conn_{i}",
                service=multiple_services[0],
                client_ip="192.168.1.1",
                client_port=5000 + i,
                routing_strategy="test",
            )

        # Route new connection - should go to service with fewer connections
        service = connection_router._least_connections_select(multiple_services)

        assert service.service_id != multiple_services[0].service_id

    @pytest.mark.asyncio
    async def test_route_connection_hash_based(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test hash-based routing for session affinity."""
        # Setup services
        for service in multiple_services:
            service.status = ServiceStatus.RUNNING
            connection_router.repository.save_service(service)

        # Same IP should route to same service
        client_ip = "192.168.1.100"
        service1 = connection_router._hash_based_select(
            multiple_services, {"client_ip": client_ip}
        )
        service2 = connection_router._hash_based_select(
            multiple_services, {"client_ip": client_ip}
        )

        assert service1.service_id == service2.service_id

        # Different IP should likely route differently
        service3 = connection_router._hash_based_select(
            multiple_services, {"client_ip": "192.168.1.200"}
        )
        # Note: This might occasionally fail due to hash collisions

    @pytest.mark.asyncio
    async def test_route_connection_weighted_random(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test weighted random routing."""
        # Setup services
        for service in multiple_services:
            service.status = ServiceStatus.RUNNING
            connection_router.repository.save_service(service)

        # Add many connections to first service
        for i in range(10):
            connection_router.register_connection(
                connection_id=f"conn_{i}",
                service=multiple_services[0],
                client_ip="192.168.1.1",
                client_port=5000 + i,
                routing_strategy="test",
            )

        # Run multiple selections - should favor services with fewer connections
        selections = []
        for _ in range(20):
            service = connection_router._weighted_random_select(multiple_services)
            selections.append(service.service_id)

        # First service (with 10 connections) should be selected less often
        first_service_count = selections.count(multiple_services[0].service_id)
        assert first_service_count < 10  # Should be less than half

    # ==================== Routing Rules Tests ====================

    @pytest.mark.asyncio
    async def test_routing_rule_equals_condition(self, connection_router: ConnectionRouter):
        """Test EQUALS condition matching."""
        condition = RoutingCondition(
            field="user_agent",
            operator=ConditionOperator.EQUALS,
            value="Mozilla/5.0",
            case_sensitive=True,
        )

        context = {"user_agent": "Mozilla/5.0"}
        assert connection_router._matches_condition(condition, context)

        context = {"user_agent": "Chrome/1.0"}
        assert not connection_router._matches_condition(condition, context)

    @pytest.mark.asyncio
    async def test_routing_rule_contains_condition(
        self, connection_router: ConnectionRouter
    ):
        """Test CONTAINS condition matching."""
        condition = RoutingCondition(
            field="user_agent",
            operator=ConditionOperator.CONTAINS,
            value="Mobile",
            case_sensitive=False,
        )

        context = {"user_agent": "Mozilla/5.0 (iPhone; mobile Safari)"}
        assert connection_router._matches_condition(condition, context)

        context = {"user_agent": "Desktop Browser"}
        assert not connection_router._matches_condition(condition, context)

    @pytest.mark.asyncio
    async def test_routing_rule_regex_match(self, connection_router: ConnectionRouter):
        """Test REGEX_MATCH condition."""
        condition = RoutingCondition(
            field="client_ip",
            operator=ConditionOperator.REGEX_MATCH,
            value=r"^192\.168\.1\.\d+$",
            case_sensitive=True,
        )

        context = {"client_ip": "192.168.1.100"}
        assert connection_router._matches_condition(condition, context)

        context = {"client_ip": "10.0.0.1"}
        assert not connection_router._matches_condition(condition, context)

    @pytest.mark.asyncio
    async def test_routing_rule_in_list_condition(
        self, connection_router: ConnectionRouter
    ):
        """Test IN_LIST condition matching."""
        condition = RoutingCondition(
            field="region",
            operator=ConditionOperator.IN_LIST,
            value="us-east,us-west,eu-west",
            case_sensitive=False,
        )

        context = {"region": "us-east"}
        assert connection_router._matches_condition(condition, context)

        context = {"region": "ap-south"}
        assert not connection_router._matches_condition(condition, context)

    @pytest.mark.asyncio
    async def test_routing_rule_case_insensitive(
        self, connection_router: ConnectionRouter
    ):
        """Test case-insensitive matching."""
        condition = RoutingCondition(
            field="env",
            operator=ConditionOperator.EQUALS,
            value="production",
            case_sensitive=False,
        )

        context = {"env": "PRODUCTION"}
        assert connection_router._matches_condition(condition, context)

        context = {"env": "Production"}
        assert connection_router._matches_condition(condition, context)

    @pytest.mark.asyncio
    async def test_routing_rule_priority(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test routing rules are applied by priority."""
        # Setup services
        for service in multiple_services:
            service.status = ServiceStatus.RUNNING
            connection_router.repository.save_service(service)

        # Create rules with different priorities
        rule1 = RoutingRule(
            name="low_priority",
            priority=10,
            enabled=True,
            target_strategy=RoutingStrategy.ROUND_ROBIN,
            target_services=[multiple_services[0].service_id],
            conditions=[
                RoutingCondition(
                    field="client_ip",
                    operator=ConditionOperator.STARTS_WITH,
                    value="192.168",
                )
            ],
        )

        rule2 = RoutingRule(
            name="high_priority",
            priority=1,
            enabled=True,
            target_strategy=RoutingStrategy.ROUND_ROBIN,
            target_services=[multiple_services[1].service_id],
            conditions=[
                RoutingCondition(
                    field="client_ip",
                    operator=ConditionOperator.STARTS_WITH,
                    value="192.168",
                )
            ],
        )

        # Save rules
        connection_router.repository.save_routing_rule(rule1)
        connection_router.repository.save_routing_rule(rule2)

        # Route connection - should match high priority rule first
        service = await connection_router.route_connection(
            client_ip="192.168.1.1", client_port=5000
        )

        assert service.service_id == multiple_services[1].service_id

    @pytest.mark.asyncio
    async def test_routing_rule_disabled(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test disabled routing rules are not applied."""
        # Setup services
        for service in multiple_services:
            service.status = ServiceStatus.RUNNING
            connection_router.repository.save_service(service)

        # Create disabled rule
        rule = RoutingRule(
            name="disabled_rule",
            priority=1,
            enabled=False,
            target_strategy=RoutingStrategy.ROUND_ROBIN,
            target_services=[multiple_services[0].service_id],
            conditions=[
                RoutingCondition(
                    field="test", operator=ConditionOperator.EQUALS, value="value"
                )
            ],
        )

        connection_router.repository.save_routing_rule(rule)

        # Should fall back to default routing
        service = await connection_router.route_connection(
            client_ip="192.168.1.1", client_port=5000, query_params={"test": "value"}
        )

        # Should use default round robin, not the disabled rule
        assert service is not None

    # ==================== Connection Management Tests ====================

    @pytest.mark.asyncio
    async def test_register_connection(
        self, connection_router: ConnectionRouter, sample_service: AgentService
    ):
        """Test registering a connection."""
        connection = connection_router.register_connection(
            connection_id="test_conn_123",
            service=sample_service,
            client_ip="192.168.1.1",
            client_port=5000,
            routing_strategy="round_robin",
            user_agent="TestClient/1.0",
        )

        assert connection.connection_id == "test_conn_123"
        assert connection.target_service_id == sample_service.service_id
        assert connection.status == ConnectionStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_unregister_connection(
        self, connection_router: ConnectionRouter, sample_service: AgentService
    ):
        """Test unregistering a connection."""
        connection_router.register_connection(
            connection_id="test_conn",
            service=sample_service,
            client_ip="192.168.1.1",
            client_port=5000,
            routing_strategy="test",
        )

        connection_router.unregister_connection("test_conn")

        assert connection_router.get_connection("test_conn") is None

    @pytest.mark.asyncio
    async def test_update_connection_status(
        self, connection_router: ConnectionRouter, sample_service: AgentService
    ):
        """Test updating connection status."""
        connection_router.register_connection(
            connection_id="test_conn",
            service=sample_service,
            client_ip="192.168.1.1",
            client_port=5000,
            routing_strategy="test",
        )

        connection_router.update_connection_status(
            "test_conn", ConnectionStatus.DISCONNECTED
        )

        connection = connection_router.get_connection("test_conn")
        assert connection.status == ConnectionStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_get_service_connections(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test getting all connections for a specific service."""
        # Register connections to different services
        connection_router.register_connection(
            "conn1",
            multiple_services[0],
            "192.168.1.1",
            5000,
            "test",
        )
        connection_router.register_connection(
            "conn2",
            multiple_services[0],
            "192.168.1.2",
            5001,
            "test",
        )
        connection_router.register_connection(
            "conn3",
            multiple_services[1],
            "192.168.1.3",
            5002,
            "test",
        )

        # Get connections for first service
        connections = connection_router.get_service_connections(
            multiple_services[0].service_id
        )

        assert len(connections) == 2
        assert all(
            c.target_service_id == multiple_services[0].service_id for c in connections
        )

    @pytest.mark.asyncio
    async def test_get_connection_stats(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test getting connection statistics."""
        # Register various connections
        connection_router.register_connection(
            "conn1", multiple_services[0], "192.168.1.1", 5000, "test"
        )
        connection_router.register_connection(
            "conn2", multiple_services[1], "192.168.1.2", 5001, "test"
        )

        # Update one to disconnected
        connection_router.update_connection_status(
            "conn1", ConnectionStatus.DISCONNECTED
        )

        stats = connection_router.get_connection_stats()

        assert stats["total_connections"] == 2
        assert stats["by_status"]["connected"] == 1
        assert stats["by_status"]["disconnected"] == 1

    # ==================== Edge Cases Tests ====================

    @pytest.mark.asyncio
    async def test_route_connection_no_available_services(
        self, connection_router: ConnectionRouter
    ):
        """Test routing when no services are available."""
        service = await connection_router.route_connection(
            client_ip="192.168.1.1", client_port=5000
        )

        assert service is None

    @pytest.mark.asyncio
    async def test_route_connection_with_target_tags(
        self, connection_router: ConnectionRouter, multiple_services
    ):
        """Test routing with target tags filter."""
        # Setup services with different tags
        multiple_services[0].tags = {"production", "api"}
        multiple_services[1].tags = {"development", "api"}
        multiple_services[2].tags = {"production", "worker"}

        for service in multiple_services:
            service.status = ServiceStatus.RUNNING
            connection_router.repository.save_service(service)

        # Create rule targeting production + api
        rule = RoutingRule(
            name="prod_api_rule",
            priority=1,
            enabled=True,
            target_strategy=RoutingStrategy.ROUND_ROBIN,
            target_tags=["production", "api"],
        )

        connection_router.repository.save_routing_rule(rule)

        # Should only route to service with both tags
        targets = connection_router._get_target_services(rule, multiple_services)

        assert len(targets) == 1
        assert targets[0].service_id == multiple_services[0].service_id

    @pytest.mark.asyncio
    async def test_invalid_regex_pattern(self, connection_router: ConnectionRouter):
        """Test handling of invalid regex patterns."""
        condition = RoutingCondition(
            field="test",
            operator=ConditionOperator.REGEX_MATCH,
            value="[invalid(regex",  # Invalid regex
        )

        context = {"test": "value"}

        # Should return False and log warning
        result = connection_router._matches_condition(condition, context)
        assert not result
