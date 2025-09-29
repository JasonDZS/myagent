"""API request/response models."""

from datetime import datetime
from typing import Dict, List, Optional, Set, Any

from pydantic import BaseModel, Field

from ..storage.models import ServiceStatus, ConnectionStatus, RoutingStrategy


# Request Models

class ServiceCreateRequest(BaseModel):
    """Request model for creating a service."""
    
    name: str = Field(..., description="Service name (unique)")
    agent_factory_path: str = Field(..., description="Path to agent factory file")
    host: str = Field(default="localhost", description="Service host")
    port: Optional[int] = Field(default=None, description="Service port (auto-allocated if not specified)")
    description: str = Field(default="", description="Service description")
    tags: Set[str] = Field(default_factory=set, description="Service tags")
    auto_start: bool = Field(default=False, description="Auto start after creation")
    
    # Configuration
    max_sessions: int = Field(default=0, description="Maximum concurrent sessions")
    session_timeout: int = Field(default=1800, description="Session timeout in seconds")
    auto_restart: bool = Field(default=True, description="Enable auto restart")
    max_restart_count: int = Field(default=3, description="Maximum restart attempts")
    health_check_enabled: bool = Field(default=True, description="Enable health checks")


class ServiceUpdateRequest(BaseModel):
    """Request model for updating a service."""
    
    description: Optional[str] = None
    tags: Optional[Set[str]] = None
    max_sessions: Optional[int] = None
    session_timeout: Optional[int] = None
    auto_restart: Optional[bool] = None
    max_restart_count: Optional[int] = None
    health_check_enabled: Optional[bool] = None


class RoutingRuleCreateRequest(BaseModel):
    """Request model for creating a routing rule."""
    
    name: str = Field(..., description="Rule name (unique)")
    priority: int = Field(default=100, description="Rule priority (lower = higher priority)")
    enabled: bool = Field(default=True, description="Enable rule")
    target_strategy: RoutingStrategy = Field(default=RoutingStrategy.ROUND_ROBIN, description="Routing strategy")
    target_services: List[str] = Field(default_factory=list, description="Target service IDs")
    target_tags: List[str] = Field(default_factory=list, description="Target service tags")
    weight: int = Field(default=1, description="Rule weight")
    description: str = Field(default="", description="Rule description")


# Response Models

class ServiceResponse(BaseModel):
    """Response model for service information."""
    
    service_id: str
    name: str
    description: str
    host: str
    port: int
    endpoint: str
    tags: Set[str]
    agent_type: str
    version: str
    status: ServiceStatus
    created_at: datetime
    started_at: Optional[datetime]
    last_health_check: Optional[datetime]
    error_message: Optional[str]
    restart_count: int


class ServiceStatsResponse(BaseModel):
    """Response model for service statistics."""
    
    total_connections: int
    active_connections: int
    peak_connections: int
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    failed_sessions: int
    avg_session_duration: float
    avg_response_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    error_count: int
    error_rate: float
    uptime_seconds: int


class ConnectionResponse(BaseModel):
    """Response model for connection information."""
    
    connection_id: str
    session_id: Optional[str]
    client_ip: str
    client_port: int
    user_agent: Optional[str]
    target_service_id: str
    routing_strategy: str
    status: ConnectionStatus
    connected_at: datetime
    last_activity: datetime
    bytes_sent: int
    bytes_received: int
    message_count: int


class HealthCheckResponse(BaseModel):
    """Response model for health check result."""
    
    service_id: str
    timestamp: datetime
    status: str
    response_time_ms: float
    checks: Dict[str, Dict[str, Any]]
    error_message: Optional[str]


class SystemStatsResponse(BaseModel):
    """Response model for system statistics."""
    
    services: Dict[str, int]
    connections: Dict[str, Any]
    health: Dict[str, int]


class RoutingRuleResponse(BaseModel):
    """Response model for routing rule."""
    
    rule_id: str
    name: str
    priority: int
    enabled: bool
    target_strategy: RoutingStrategy
    target_services: List[str]
    target_tags: List[str]
    weight: int
    description: str
    created_at: datetime
    updated_at: datetime


# Generic Response Models

class SuccessResponse(BaseModel):
    """Generic success response."""
    
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    
    success: bool = False
    error: str
    detail: Optional[str] = None


class ListResponse(BaseModel):
    """Generic list response with pagination."""
    
    items: List[Any]
    total: int
    limit: Optional[int] = None
    offset: int = 0
    has_more: bool = False