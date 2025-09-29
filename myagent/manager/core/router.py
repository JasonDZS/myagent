"""Connection router for load balancing and routing connections."""

import asyncio
import hashlib
import random
import re
from collections import defaultdict
from typing import Dict, List, Optional, Any

from myagent.logger import logger
from ..storage.models import (
    AgentService,
    ConnectionInfo,
    RoutingRule,
    RoutingStrategy,
    RoutingCondition,
    ConditionOperator,
    ConnectionStatus,
)
from ..storage.repository import ServiceRepository


class ConnectionRouter:
    """Routes client connections to appropriate agent services."""
    
    def __init__(self, repository: ServiceRepository):
        self.repository = repository
        self._active_connections: Dict[str, ConnectionInfo] = {}
        self._round_robin_counters: Dict[str, int] = defaultdict(int)
    
    async def route_connection(
        self,
        client_ip: str,
        client_port: int,
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[AgentService]:
        """Route a new connection to an appropriate service."""
        
        # Get available services
        available_services = self._get_available_services()
        if not available_services:
            logger.warning("No available services for routing")
            return None
        
        # Get routing rules
        routing_rules = self.repository.get_routing_rules(enabled_only=True)
        
        # Build routing context
        context = {
            "client_ip": client_ip,
            "client_port": client_port,
            "user_agent": user_agent or "",
            **(headers or {}),
            **(query_params or {}),
        }
        
        # Apply routing rules in priority order
        for rule in routing_rules:
            if self._matches_rule(rule, context):
                target_services = self._get_target_services(rule, available_services)
                if target_services:
                    selected = self._select_service(rule.target_strategy, target_services, context)
                    if selected:
                        logger.info(f"Routed connection to service '{selected.name}' using rule '{rule.name}'")
                        return selected
        
        # Fallback to default routing
        selected = self._select_service(RoutingStrategy.ROUND_ROBIN, available_services, context)
        if selected:
            logger.info(f"Routed connection to service '{selected.name}' using default strategy")
        
        return selected
    
    def register_connection(
        self,
        connection_id: str,
        service: AgentService,
        client_ip: str,
        client_port: int,
        routing_strategy: str,
        user_agent: Optional[str] = None,
    ) -> ConnectionInfo:
        """Register a new connection."""
        
        connection = ConnectionInfo(
            connection_id=connection_id,
            client_ip=client_ip,
            client_port=client_port,
            user_agent=user_agent,
            target_service_id=service.service_id,
            routing_strategy=routing_strategy,
            status=ConnectionStatus.CONNECTED,
        )
        
        self._active_connections[connection_id] = connection
        logger.info(f"Registered connection {connection_id} to service '{service.name}'")
        
        return connection
    
    def update_connection_status(self, connection_id: str, status: ConnectionStatus):
        """Update connection status."""
        from datetime import datetime
        if connection_id in self._active_connections:
            self._active_connections[connection_id].status = status
            self._active_connections[connection_id].last_activity = datetime.now()
    
    def unregister_connection(self, connection_id: str):
        """Unregister a connection."""
        if connection_id in self._active_connections:
            connection = self._active_connections.pop(connection_id)
            logger.info(f"Unregistered connection {connection_id} from service {connection.target_service_id}")
    
    def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection info."""
        return self._active_connections.get(connection_id)
    
    def get_service_connections(self, service_id: str) -> List[ConnectionInfo]:
        """Get all connections for a service."""
        return [
            conn for conn in self._active_connections.values()
            if conn.target_service_id == service_id
        ]
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total = len(self._active_connections)
        by_status = defaultdict(int)
        by_service = defaultdict(int)
        
        for conn in self._active_connections.values():
            by_status[conn.status.value] += 1
            by_service[conn.target_service_id] += 1
        
        return {
            "total_connections": total,
            "by_status": dict(by_status),
            "by_service": dict(by_service),
        }
    
    def _get_available_services(self) -> List[AgentService]:
        """Get services that are available for routing."""
        from ..storage.models import ServiceStatus
        return self.repository.list_services(status=ServiceStatus.RUNNING)
    
    def _matches_rule(self, rule: RoutingRule, context: Dict[str, Any]) -> bool:
        """Check if routing rule matches the context."""
        if not rule.conditions:
            return True  # Rule with no conditions matches everything
        
        for condition in rule.conditions:
            if not self._matches_condition(condition, context):
                return False
        
        return True
    
    def _matches_condition(self, condition: RoutingCondition, context: Dict[str, Any]) -> bool:
        """Check if a single condition matches."""
        field_value = str(context.get(condition.field, ""))
        target_value = condition.value
        
        if not condition.case_sensitive:
            field_value = field_value.lower()
            target_value = target_value.lower()
        
        if condition.operator == ConditionOperator.EQUALS:
            return field_value == target_value
        elif condition.operator == ConditionOperator.NOT_EQUALS:
            return field_value != target_value
        elif condition.operator == ConditionOperator.CONTAINS:
            return target_value in field_value
        elif condition.operator == ConditionOperator.NOT_CONTAINS:
            return target_value not in field_value
        elif condition.operator == ConditionOperator.STARTS_WITH:
            return field_value.startswith(target_value)
        elif condition.operator == ConditionOperator.ENDS_WITH:
            return field_value.endswith(target_value)
        elif condition.operator == ConditionOperator.REGEX_MATCH:
            try:
                flags = 0 if condition.case_sensitive else re.IGNORECASE
                return bool(re.search(target_value, field_value, flags))
            except re.error:
                logger.warning(f"Invalid regex pattern: {target_value}")
                return False
        elif condition.operator == ConditionOperator.IN_LIST:
            values = [v.strip() for v in target_value.split(",")]
            if not condition.case_sensitive:
                values = [v.lower() for v in values]
            return field_value in values
        elif condition.operator == ConditionOperator.NOT_IN_LIST:
            values = [v.strip() for v in target_value.split(",")]
            if not condition.case_sensitive:
                values = [v.lower() for v in values]
            return field_value not in values
        
        return False
    
    def _get_target_services(self, rule: RoutingRule, available_services: List[AgentService]) -> List[AgentService]:
        """Get target services for a routing rule."""
        targets = []
        
        # Filter by service IDs
        if rule.target_services:
            service_ids = set(rule.target_services)
            targets.extend([s for s in available_services if s.service_id in service_ids])
        
        # Filter by tags
        elif rule.target_tags:
            target_tags = set(rule.target_tags)
            targets.extend([
                s for s in available_services 
                if target_tags.intersection(s.tags)
            ])
        else:
            # No specific targets, use all available services
            targets = available_services[:]
        
        return targets
    
    def _select_service(
        self, 
        strategy: RoutingStrategy, 
        services: List[AgentService], 
        context: Dict[str, Any]
    ) -> Optional[AgentService]:
        """Select a service using the specified strategy."""
        if not services:
            return None
        
        if strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_select(services)
        elif strategy == RoutingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(services)
        elif strategy == RoutingStrategy.WEIGHTED_RANDOM:
            return self._weighted_random_select(services)
        elif strategy == RoutingStrategy.HASH_BASED:
            return self._hash_based_select(services, context)
        elif strategy == RoutingStrategy.TAG_BASED:
            return self._tag_based_select(services, context)
        else:
            # Fallback to round robin
            return self._round_robin_select(services)
    
    def _round_robin_select(self, services: List[AgentService]) -> AgentService:
        """Round robin selection."""
        key = "default"
        counter = self._round_robin_counters[key]
        service = services[counter % len(services)]
        self._round_robin_counters[key] = (counter + 1) % len(services)
        return service
    
    def _least_connections_select(self, services: List[AgentService]) -> AgentService:
        """Least connections selection."""
        min_connections = float('inf')
        selected = services[0]
        
        for service in services:
            connection_count = len(self.get_service_connections(service.service_id))
            if connection_count < min_connections:
                min_connections = connection_count
                selected = service
        
        return selected
    
    def _weighted_random_select(self, services: List[AgentService]) -> AgentService:
        """Weighted random selection based on inverse connection count."""
        if len(services) == 1:
            return services[0]
        
        weights = []
        for service in services:
            connection_count = len(self.get_service_connections(service.service_id))
            # Use inverse weight (fewer connections = higher weight)
            weight = 1.0 / (connection_count + 1)
            weights.append(weight)
        
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(services)
        
        # Weighted random selection
        r = random.uniform(0, total_weight)
        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return services[i]
        
        return services[-1]  # Fallback
    
    def _hash_based_select(self, services: List[AgentService], context: Dict[str, Any]) -> AgentService:
        """Hash-based selection for session affinity."""
        # Use client IP as hash key for session affinity
        client_ip = context.get("client_ip", "")
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(services)
        return services[index]
    
    def _tag_based_select(self, services: List[AgentService], context: Dict[str, Any]) -> AgentService:
        """Tag-based selection with fallback to round robin."""
        # This is a simple implementation - can be enhanced with more sophisticated logic
        # For now, just use round robin among tag-filtered services
        return self._round_robin_select(services)