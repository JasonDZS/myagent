"""FastAPI server for WebSocket management system."""

import asyncio
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from myagent.logger import logger
from ..core.manager import AgentManager
from ..storage.models import ServiceStatus, ServiceConfig, RoutingRule, RoutingCondition, ConditionOperator
from .models import (
    ServiceCreateRequest,
    ServiceUpdateRequest,
    ServiceResponse,
    ServiceStatsResponse,
    ConnectionResponse,
    HealthCheckResponse,
    SystemStatsResponse,
    RoutingRuleCreateRequest,
    RoutingRuleResponse,
    SuccessResponse,
    ErrorResponse,
    ListResponse,
)


class APIServer:
    """FastAPI server for management system."""
    
    def __init__(self, manager: AgentManager):
        self.manager = manager
        self.app = FastAPI(
            title="MyAgent Management API",
            description="HTTP API for MyAgent WebSocket Management System",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes()
        
        # Add exception handlers
        self._register_exception_handlers()
    
    def _register_exception_handlers(self):
        """Register custom exception handlers."""
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request, exc):
            logger.error(f"API error: {exc}")
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Internal server error",
                    detail=str(exc)
                ).model_dump()
            )
    
    def _register_routes(self):
        """Register all API routes."""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": "2025-09-28T18:30:00Z"}
        
        # System info
        @self.app.get("/api/v1/info")
        async def get_system_info():
            return {
                "name": "MyAgent Management System",
                "version": "1.0.0",
                "description": "WebSocket management system for multi-agent deployments"
            }
        
        # Services
        
        @self.app.post("/api/v1/services", response_model=ServiceResponse)
        async def create_service(request: ServiceCreateRequest):
            """Create a new service."""
            try:
                # Create service config
                config = ServiceConfig(
                    agent_factory_path=request.agent_factory_path,
                    max_sessions=request.max_sessions,
                    session_timeout=request.session_timeout,
                    auto_restart=request.auto_restart,
                    max_restart_count=request.max_restart_count,
                    health_check_enabled=request.health_check_enabled,
                )
                
                # Register service
                service = await self.manager.register_service(
                    name=request.name,
                    agent_factory_path=request.agent_factory_path,
                    host=request.host,
                    port=request.port,
                    description=request.description,
                    tags=request.tags,
                    config=config,
                    auto_start=request.auto_start,
                )
                
                if not service:
                    raise HTTPException(status_code=400, detail="Failed to create service")
                
                return ServiceResponse(**service.model_dump())
                
            except Exception as e:
                logger.error(f"Failed to create service: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/services", response_model=ListResponse)
        async def list_services(
            status: Optional[ServiceStatus] = Query(None, description="Filter by status"),
            tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
            limit: Optional[int] = Query(None, description="Limit number of results"),
            offset: int = Query(0, description="Offset for pagination"),
        ):
            """List services with optional filters."""
            try:
                # Parse tags
                tag_list = None
                if tags:
                    tag_list = [tag.strip() for tag in tags.split(",")]
                
                # Get services
                services = self.manager.list_services(
                    status=status,
                    tags=tag_list,
                    limit=limit,
                    offset=offset,
                )
                
                # Convert to response format
                service_responses = [
                    ServiceResponse(**service.model_dump())
                    for service in services
                ]
                
                return ListResponse(
                    items=service_responses,
                    total=len(service_responses),
                    limit=limit,
                    offset=offset,
                    has_more=False  # TODO: Implement proper pagination
                )
                
            except Exception as e:
                logger.error(f"Failed to list services: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/services/{service_id}", response_model=ServiceResponse)
        async def get_service(service_id: str = Path(..., description="Service ID")):
            """Get service by ID."""
            try:
                service = self.manager.get_service(service_id)
                if not service:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                return ServiceResponse(**service.model_dump())
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get service: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.put("/api/v1/services/{service_id}", response_model=ServiceResponse)
        async def update_service(
            service_id: str = Path(..., description="Service ID"),
            request: ServiceUpdateRequest = None
        ):
            """Update service configuration."""
            try:
                service = self.manager.get_service(service_id)
                if not service:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                # Update fields
                if request.description is not None:
                    service.description = request.description
                if request.tags is not None:
                    service.tags = request.tags
                if request.max_sessions is not None:
                    service.config.max_sessions = request.max_sessions
                if request.session_timeout is not None:
                    service.config.session_timeout = request.session_timeout
                if request.auto_restart is not None:
                    service.config.auto_restart = request.auto_restart
                if request.max_restart_count is not None:
                    service.config.max_restart_count = request.max_restart_count
                if request.health_check_enabled is not None:
                    service.config.health_check_enabled = request.health_check_enabled
                
                # Save changes
                self.manager.repository.save_service(service)
                
                return ServiceResponse(**service.model_dump())
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update service: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/v1/services/{service_id}", response_model=SuccessResponse)
        async def delete_service(service_id: str = Path(..., description="Service ID")):
            """Delete a service."""
            try:
                success = await self.manager.unregister_service(service_id)
                if not success:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                return SuccessResponse(message="Service deleted successfully")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to delete service: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Service Control
        
        @self.app.post("/api/v1/services/{service_id}/start", response_model=SuccessResponse)
        async def start_service(service_id: str = Path(..., description="Service ID")):
            """Start a service."""
            try:
                success = await self.manager.start_service(service_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to start service")
                
                return SuccessResponse(message="Service started successfully")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to start service: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/services/{service_id}/stop", response_model=SuccessResponse)
        async def stop_service(service_id: str = Path(..., description="Service ID")):
            """Stop a service."""
            try:
                success = await self.manager.stop_service(service_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to stop service")
                
                return SuccessResponse(message="Service stopped successfully")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to stop service: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/services/{service_id}/restart", response_model=SuccessResponse)
        async def restart_service(service_id: str = Path(..., description="Service ID")):
            """Restart a service."""
            try:
                success = await self.manager.restart_service(service_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to restart service")
                
                return SuccessResponse(message="Service restarted successfully")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to restart service: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Service Statistics
        
        @self.app.get("/api/v1/services/{service_id}/stats", response_model=ServiceStatsResponse)
        async def get_service_stats(service_id: str = Path(..., description="Service ID")):
            """Get service statistics."""
            try:
                service = self.manager.get_service(service_id)
                if not service:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                return ServiceStatsResponse(**service.stats.model_dump())
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get service stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Health Checks
        
        @self.app.get("/api/v1/services/{service_id}/health", response_model=HealthCheckResponse)
        async def check_service_health(service_id: str = Path(..., description="Service ID")):
            """Check service health."""
            try:
                result = await self.manager.check_service_health(service_id)
                if not result:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                # Convert checks to dict format
                checks_dict = {}
                for name, check in result.checks.items():
                    checks_dict[name] = check.model_dump()
                
                return HealthCheckResponse(
                    service_id=result.service_id,
                    timestamp=result.timestamp,
                    status=result.status.value,
                    response_time_ms=result.response_time_ms,
                    checks=checks_dict,
                    error_message=result.error_message,
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to check service health: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Connections
        
        @self.app.get("/api/v1/connections", response_model=ListResponse)
        async def list_connections():
            """List active connections."""
            try:
                connections = self.manager.get_active_connections()
                
                # Convert ConnectionInfo objects to dict for JSON serialization
                connection_items = []
                for conn in connections:
                    connection_items.append({
                        "connection_id": conn.connection_id,
                        "session_id": conn.session_id,
                        "client_ip": conn.client_ip,
                        "client_port": conn.client_port,
                        "user_agent": conn.user_agent,
                        "target_service_id": conn.target_service_id,
                        "routing_strategy": conn.routing_strategy,
                        "status": conn.status.value,
                        "connected_at": conn.connected_at.isoformat(),
                        "last_activity": conn.last_activity.isoformat(),
                        "bytes_sent": conn.bytes_sent,
                        "bytes_received": conn.bytes_received,
                        "message_count": conn.message_count,
                    })
                
                return ListResponse(
                    items=connection_items,
                    total=len(connection_items),
                    offset=0,
                    has_more=False
                )
                
            except Exception as e:
                logger.error(f"Failed to list connections: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/v1/connections/{connection_id}")
        async def disconnect_connection(connection_id: str):
            """Disconnect a specific connection."""
            try:
                # Get connection info before disconnecting
                connection = self.manager.router.get_connection(connection_id)
                if not connection:
                    raise HTTPException(status_code=404, detail="Connection not found")
                
                # Unregister the connection (this will trigger cleanup in proxy)
                self.manager.unregister_connection(connection_id)
                
                return {"message": f"Connection {connection_id} disconnected successfully"}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to disconnect connection {connection_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # System Statistics
        
        @self.app.get("/api/v1/stats", response_model=SystemStatsResponse)
        async def get_system_stats():
            """Get system statistics."""
            try:
                stats = self.manager.get_system_stats()
                return SystemStatsResponse(**stats)
                
            except Exception as e:
                logger.error(f"Failed to get system stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Routing Rules
        
        @self.app.post("/api/v1/routing/rules", response_model=RoutingRuleResponse)
        async def create_routing_rule(request: RoutingRuleCreateRequest):
            """Create a routing rule."""
            try:
                rule = RoutingRule(
                    name=request.name,
                    priority=request.priority,
                    enabled=request.enabled,
                    target_strategy=request.target_strategy,
                    target_services=request.target_services,
                    target_tags=request.target_tags,
                    weight=request.weight,
                    description=request.description,
                )
                
                success = self.manager.add_routing_rule(rule)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to create routing rule")
                
                return RoutingRuleResponse(**rule.model_dump())
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to create routing rule: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/routing/rules", response_model=ListResponse)
        async def list_routing_rules(
            enabled_only: bool = Query(True, description="Only return enabled rules")
        ):
            """List routing rules."""
            try:
                rules = self.manager.get_routing_rules(enabled_only=enabled_only)
                
                rule_responses = [
                    RoutingRuleResponse(**rule.model_dump())
                    for rule in rules
                ]
                
                return ListResponse(
                    items=rule_responses,
                    total=len(rule_responses),
                    offset=0,
                    has_more=False
                )
                
            except Exception as e:
                logger.error(f"Failed to list routing rules: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def start(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the API server."""
        import uvicorn
        
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        logger.info(f"Starting API server on http://{host}:{port}")
        logger.info(f"API documentation available at http://{host}:{port}/docs")
        
        await server.serve()