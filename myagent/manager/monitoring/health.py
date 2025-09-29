"""Health monitoring for agent services."""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

import websockets
from websockets.exceptions import WebSocketException

from myagent.logger import logger
from ..storage.models import (
    AgentService,
    HealthCheckResult,
    CheckResult,
    HealthStatus,
    ServiceStatus,
)
from ..storage.repository import ServiceRepository


class HealthMonitor:
    """Monitor health of agent services."""
    
    def __init__(self, repository: ServiceRepository):
        self.repository = repository
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._check_interval = 10  # seconds
    
    async def start_monitoring(self, interval: int = 10):
        """Start health monitoring."""
        if self._monitoring:
            logger.warning("Health monitoring is already running")
            return
        
        self._check_interval = interval
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Started health monitoring with {interval}s interval")
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped health monitoring")
    
    async def check_service_health(self, service: AgentService) -> HealthCheckResult:
        """Perform health check on a single service."""
        start_time = time.time()
        checks = {}
        overall_status = HealthStatus.HEALTHY
        error_message = None
        
        try:
            # Check 1: WebSocket connectivity
            ws_check = await self._check_websocket_connectivity(service)
            checks["websocket"] = ws_check
            
            if ws_check.status != HealthStatus.HEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            
            # Check 2: Service status
            status_check = self._check_service_status(service)
            checks["status"] = status_check
            
            if status_check.status != HealthStatus.HEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            
            # Check 3: Resource usage (if available)
            resource_check = await self._check_resource_usage(service)
            if resource_check:
                checks["resources"] = resource_check
                if resource_check.status == HealthStatus.DEGRADED:
                    overall_status = HealthStatus.DEGRADED
        
        except Exception as e:
            logger.error(f"Health check failed for service '{service.name}': {e}")
            overall_status = HealthStatus.UNHEALTHY
            error_message = str(e)
        
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        result = HealthCheckResult(
            service_id=service.service_id,
            status=overall_status,
            response_time_ms=response_time,
            checks=checks,
            error_message=error_message,
        )
        
        # Save result to repository
        self.repository.save_health_check(result)
        
        # Update service health status
        service.last_health_check = datetime.now()
        if overall_status == HealthStatus.UNHEALTHY and service.status == ServiceStatus.RUNNING:
            service.status = ServiceStatus.UNHEALTHY
            service.error_message = error_message
            self.repository.save_service(service)
        elif overall_status == HealthStatus.HEALTHY and service.status == ServiceStatus.UNHEALTHY:
            service.status = ServiceStatus.RUNNING
            service.error_message = None
            self.repository.save_service(service)
        
        return result
    
    async def check_all_services(self) -> List[HealthCheckResult]:
        """Check health of all running services."""
        services = self.repository.list_services(status=ServiceStatus.RUNNING)
        services.extend(self.repository.list_services(status=ServiceStatus.UNHEALTHY))
        
        results = []
        for service in services:
            try:
                result = await self.check_service_health(service)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to check health for service '{service.name}': {e}")
        
        return results
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                logger.debug("Performing health checks...")
                results = await self.check_all_services()
                
                # Log summary
                healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
                total_count = len(results)
                logger.debug(f"Health check completed: {healthy_count}/{total_count} services healthy")
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
            
            await asyncio.sleep(self._check_interval)
    
    async def _check_websocket_connectivity(self, service: AgentService) -> CheckResult:
        """Check WebSocket connectivity."""
        start_time = time.time()
        
        try:
            # Try to connect to the WebSocket endpoint
            uri = service.endpoint
            async with websockets.connect(uri, ping_timeout=5, close_timeout=5) as websocket:
                # Send a simple ping message
                await websocket.send('{"type": "ping"}')
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    duration = (time.time() - start_time) * 1000
                    
                    return CheckResult(
                        name="websocket",
                        status=HealthStatus.HEALTHY,
                        message="WebSocket connection successful",
                        duration_ms=duration,
                        metadata={"response": response[:100]}  # Truncate response
                    )
                except asyncio.TimeoutError:
                    duration = (time.time() - start_time) * 1000
                    return CheckResult(
                        name="websocket",
                        status=HealthStatus.DEGRADED,
                        message="WebSocket connection timeout",
                        duration_ms=duration,
                    )
        
        except WebSocketException as e:
            duration = (time.time() - start_time) * 1000
            return CheckResult(
                name="websocket",
                status=HealthStatus.UNHEALTHY,
                message=f"WebSocket error: {e}",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return CheckResult(
                name="websocket",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection error: {e}",
                duration_ms=duration,
            )
    
    def _check_service_status(self, service: AgentService) -> CheckResult:
        """Check service status."""
        start_time = time.time()
        
        if service.status == ServiceStatus.RUNNING:
            status = HealthStatus.HEALTHY
            message = "Service is running normally"
        elif service.status == ServiceStatus.UNHEALTHY:
            status = HealthStatus.UNHEALTHY
            message = f"Service is unhealthy: {service.error_message or 'Unknown error'}"
        elif service.status == ServiceStatus.ERROR:
            status = HealthStatus.UNHEALTHY
            message = f"Service error: {service.error_message or 'Unknown error'}"
        else:
            status = HealthStatus.UNHEALTHY
            message = f"Service not running (status: {service.status.value})"
        
        duration = (time.time() - start_time) * 1000
        
        return CheckResult(
            name="status",
            status=status,
            message=message,
            duration_ms=duration,
            metadata={"service_status": service.status.value}
        )
    
    async def _check_resource_usage(self, service: AgentService) -> Optional[CheckResult]:
        """Check resource usage (placeholder for future implementation)."""
        # This would require integration with system monitoring tools
        # For now, return None to indicate this check is not implemented
        return None
    
    def get_service_health_history(self, service_id: str, limit: int = 10) -> List[HealthCheckResult]:
        """Get health check history for a service."""
        return self.repository.get_health_history(service_id, limit)
    
    def get_health_summary(self) -> Dict[str, int]:
        """Get overall health summary."""
        services = self.repository.list_services()
        
        summary = {
            "total": len(services),
            "healthy": 0,
            "unhealthy": 0,
            "degraded": 0,
            "unknown": 0,
        }
        
        for service in services:
            if service.status == ServiceStatus.RUNNING:
                summary["healthy"] += 1
            elif service.status == ServiceStatus.UNHEALTHY:
                summary["unhealthy"] += 1
            elif service.status == ServiceStatus.ERROR:
                summary["unhealthy"] += 1
            else:
                summary["unknown"] += 1
        
        return summary