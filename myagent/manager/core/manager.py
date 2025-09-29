"""Core agent manager for WebSocket management system."""

import asyncio
from typing import Dict, List, Optional, Set

from myagent.logger import logger
from ..storage.models import AgentService, ServiceConfig, ServiceStatus, RoutingRule
from ..storage.repository import ServiceRepository
from .registry import ServiceRegistry
from .router import ConnectionRouter
from ..monitoring.health import HealthMonitor


class AgentManager:
    """Central manager for agent services."""
    
    def __init__(self, db_path: str = "agent_manager.db"):
        self.repository = ServiceRepository(db_path)
        self.registry = ServiceRegistry(self.repository)
        self.router = ConnectionRouter(self.repository)
        self.health_monitor = HealthMonitor(self.repository)
        
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self, health_check_interval: int = 10):
        """Start the agent manager."""
        if self._running:
            logger.warning("Agent manager is already running")
            return
        
        self._running = True
        logger.info("Starting MyAgent Manager...")
        
        # Start health monitoring
        await self.health_monitor.start_monitoring(health_check_interval)
        
        # Start auto-restart monitoring
        auto_restart_task = asyncio.create_task(self._auto_restart_loop())
        self._tasks.append(auto_restart_task)
        
        logger.info("MyAgent Manager started successfully")
    
    async def stop(self):
        """Stop the agent manager."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping MyAgent Manager...")
        
        # Stop health monitoring
        await self.health_monitor.stop_monitoring()
        
        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info("MyAgent Manager stopped")
    
    # Service Management Methods
    
    async def register_service(
        self,
        name: str,
        agent_factory_path: str,
        host: str = "localhost",
        port: Optional[int] = None,
        description: str = "",
        tags: Optional[Set[str]] = None,
        config: Optional[ServiceConfig] = None,
        auto_start: bool = False,
    ) -> Optional[AgentService]:
        """Register a new agent service."""
        service = await self.registry.register_service(
            name=name,
            agent_factory_path=agent_factory_path,
            host=host,
            port=port,
            description=description,
            tags=tags,
            config=config,
        )
        
        if service and auto_start:
            await self.start_service(service.service_id)
        
        return service
    
    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service."""
        return await self.registry.unregister_service(service_id)
    
    async def start_service(self, service_id: str) -> bool:
        """Start a service."""
        return await self.registry.start_service(service_id)
    
    async def stop_service(self, service_id: str) -> bool:
        """Stop a service."""
        return await self.registry.stop_service(service_id)
    
    async def restart_service(self, service_id: str) -> bool:
        """Restart a service."""
        return await self.registry.restart_service(service_id)
    
    async def start_all_services(self) -> Dict[str, bool]:
        """Start all registered services."""
        services = self.list_services(status=ServiceStatus.STOPPED)
        results = {}
        
        for service in services:
            success = await self.start_service(service.service_id)
            results[service.name] = success
        
        return results
    
    async def stop_all_services(self) -> Dict[str, bool]:
        """Stop all running services."""
        services = self.list_services(status=ServiceStatus.RUNNING)
        services.extend(self.list_services(status=ServiceStatus.UNHEALTHY))
        results = {}
        
        for service in services:
            success = await self.stop_service(service.service_id)
            results[service.name] = success
        
        return results
    
    def get_service(self, service_id: str) -> Optional[AgentService]:
        """Get service by ID."""
        return self.registry.get_service(service_id)
    
    def get_service_by_name(self, name: str) -> Optional[AgentService]:
        """Get service by name."""
        return self.registry.get_service_by_name(name)
    
    def list_services(
        self,
        status: Optional[ServiceStatus] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[AgentService]:
        """List services with optional filters."""
        return self.registry.list_services(status, tags, limit, offset)
    
    # Routing Management Methods
    
    async def route_connection(
        self,
        client_ip: str,
        client_port: int,
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[AgentService]:
        """Route a client connection to an appropriate service."""
        return await self.router.route_connection(
            client_ip, client_port, user_agent, headers, query_params
        )
    
    def register_connection(self, connection_id: str, service: AgentService, **kwargs):
        """Register a client connection."""
        return self.router.register_connection(connection_id, service, **kwargs)
    
    def unregister_connection(self, connection_id: str):
        """Unregister a client connection."""
        self.router.unregister_connection(connection_id)
    
    def get_connection_stats(self):
        """Get connection statistics."""
        return self.router.get_connection_stats()
    
    def get_active_connections(self):
        """Get list of active connections."""
        return list(self.router._active_connections.values())
    
    # Routing Rules Management
    
    def add_routing_rule(self, rule: RoutingRule) -> bool:
        """Add a routing rule."""
        return self.repository.save_routing_rule(rule)
    
    def get_routing_rules(self, enabled_only: bool = True) -> List[RoutingRule]:
        """Get routing rules."""
        return self.repository.get_routing_rules(enabled_only)
    
    # Health Monitoring Methods
    
    async def check_service_health(self, service_id: str):
        """Check health of a specific service."""
        service = self.get_service(service_id)
        if service:
            return await self.health_monitor.check_service_health(service)
        return None
    
    async def check_all_services_health(self):
        """Check health of all services."""
        return await self.health_monitor.check_all_services()
    
    def get_health_summary(self):
        """Get overall health summary."""
        return self.health_monitor.get_health_summary()
    
    def get_service_health_history(self, service_id: str, limit: int = 10):
        """Get health history for a service."""
        return self.health_monitor.get_service_health_history(service_id, limit)
    
    # Statistics and Monitoring
    
    def get_system_stats(self):
        """Get comprehensive system statistics."""
        services = self.list_services()
        
        stats = {
            "services": {
                "total": len(services),
                "running": len([s for s in services if s.status == ServiceStatus.RUNNING]),
                "stopped": len([s for s in services if s.status == ServiceStatus.STOPPED]),
                "error": len([s for s in services if s.status == ServiceStatus.ERROR]),
                "unhealthy": len([s for s in services if s.status == ServiceStatus.UNHEALTHY]),
            },
            "connections": self.get_connection_stats(),
            "health": self.get_health_summary(),
        }
        
        return stats
    
    # Auto-restart functionality
    
    async def _auto_restart_loop(self):
        """Monitor services for auto-restart."""
        while self._running:
            try:
                await self._check_auto_restart()
            except Exception as e:
                logger.error(f"Error in auto-restart loop: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def _check_auto_restart(self):
        """Check services that need auto-restart."""
        services = self.list_services(status=ServiceStatus.ERROR)
        services.extend(self.list_services(status=ServiceStatus.UNHEALTHY))
        
        for service in services:
            if (service.config.auto_restart and 
                service.restart_count < service.config.max_restart_count):
                
                logger.info(f"Auto-restarting service '{service.name}' (attempt {service.restart_count + 1})")
                
                # Wait for restart delay
                await asyncio.sleep(service.config.restart_delay)
                
                # Attempt restart
                success = await self.restart_service(service.service_id)
                if success:
                    logger.info(f"Service '{service.name}' auto-restarted successfully")
                else:
                    logger.error(f"Failed to auto-restart service '{service.name}'")
    
    # Context manager support
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()