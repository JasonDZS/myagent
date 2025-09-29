"""Data models for WebSocket management system."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """Service status enumeration."""
    
    STOPPED = "stopped"         # Stopped
    STARTING = "starting"       # Starting up
    RUNNING = "running"         # Running normally
    STOPPING = "stopping"       # Shutting down
    ERROR = "error"            # Error state
    UNHEALTHY = "unhealthy"    # Running but unhealthy


class ConnectionStatus(str, Enum):
    """Connection status enumeration."""
    
    CONNECTING = "connecting"   # Connecting
    CONNECTED = "connected"     # Connected
    ACTIVE = "active"          # Active (has session)
    IDLE = "idle"              # Idle
    DISCONNECTING = "disconnecting"  # Disconnecting
    DISCONNECTED = "disconnected"    # Disconnected
    ERROR = "error"            # Error state


class RoutingStrategy(str, Enum):
    """Routing strategy enumeration."""
    
    ROUND_ROBIN = "round_robin"           # Round robin
    LEAST_CONNECTIONS = "least_connections"  # Least connections
    WEIGHTED_RANDOM = "weighted_random"    # Weighted random
    HASH_BASED = "hash_based"             # Hash-based
    TAG_BASED = "tag_based"               # Tag-based
    MANUAL = "manual"                     # Manual assignment


class ConditionOperator(str, Enum):
    """Routing condition operators."""
    
    EQUALS = "equals"           # Equals
    NOT_EQUALS = "not_equals"   # Not equals
    CONTAINS = "contains"       # Contains
    NOT_CONTAINS = "not_contains"  # Does not contain
    STARTS_WITH = "starts_with"    # Starts with
    ENDS_WITH = "ends_with"        # Ends with
    REGEX_MATCH = "regex_match"    # Regex match
    IN_LIST = "in_list"            # In list
    NOT_IN_LIST = "not_in_list"    # Not in list


class HealthStatus(str, Enum):
    """Health check status."""
    
    HEALTHY = "healthy"       # Healthy
    UNHEALTHY = "unhealthy"   # Unhealthy
    DEGRADED = "degraded"     # Degraded (partial functionality)
    UNKNOWN = "unknown"       # Unknown (cannot check)


class ServiceConfig(BaseModel):
    """Service configuration."""
    
    # Agent factory
    agent_factory_path: str     # Agent factory file path
    
    # Service parameters
    max_sessions: int = 0       # Max sessions (0=unlimited)
    session_timeout: int = 1800 # Session timeout (seconds)
    heartbeat_interval: int = 30 # Heartbeat interval (seconds)
    
    # Resource limits
    memory_limit_mb: Optional[int] = None  # Memory limit (MB)
    cpu_limit_percent: Optional[int] = None  # CPU usage limit (%)
    
    # Auto restart
    auto_restart: bool = True   # Auto restart on failure
    max_restart_count: int = 3  # Max restart attempts
    restart_delay: int = 5      # Restart delay (seconds)
    
    # Health check
    health_check_enabled: bool = True # Enable health checks
    health_check_interval: int = 10   # Health check interval (seconds)
    health_check_timeout: int = 5     # Health check timeout (seconds)
    
    # Environment variables
    environment: Dict[str, str] = Field(default_factory=dict)


class ServiceStats(BaseModel):
    """Service statistics."""
    
    # Connection statistics
    total_connections: int = 0      # Total connections
    active_connections: int = 0     # Active connections
    peak_connections: int = 0       # Peak connections
    
    # Session statistics
    total_sessions: int = 0         # Total sessions
    active_sessions: int = 0        # Active sessions
    completed_sessions: int = 0     # Completed sessions
    failed_sessions: int = 0        # Failed sessions
    
    # Performance metrics
    avg_session_duration: float = 0.0 # Average session duration (seconds)
    avg_response_time: float = 0.0    # Average response time (ms)
    throughput_per_minute: float = 0.0 # Requests per minute
    
    # Resource usage
    memory_usage_mb: float = 0.0      # Memory usage (MB)
    cpu_usage_percent: float = 0.0    # CPU usage (%)
    
    # Error statistics
    error_count: int = 0           # Total errors
    error_rate: float = 0.0        # Error rate (%)
    
    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.now)
    uptime_seconds: int = 0        # Uptime (seconds)


class AgentService(BaseModel):
    """Agent service instance."""
    
    # Basic information
    service_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                    # Service name (unique)
    description: str = ""        # Service description
    
    # Network configuration
    host: str = "localhost"      # Service host
    port: int                    # Service port
    endpoint: str = ""           # WebSocket endpoint
    
    # Metadata
    tags: Set[str] = Field(default_factory=set)  # Service tags
    agent_type: str = "react"    # Agent type
    version: str = "1.0.0"       # Service version
    
    # Status information
    status: ServiceStatus = ServiceStatus.STOPPED
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    
    # Error information
    error_message: Optional[str] = None
    restart_count: int = 0
    
    # Configuration and statistics
    config: ServiceConfig
    stats: ServiceStats = Field(default_factory=ServiceStats)
    
    def model_post_init(self, __context) -> None:
        """Set endpoint after initialization."""
        if not self.endpoint:
            self.endpoint = f"ws://{self.host}:{self.port}"


class ConnectionInfo(BaseModel):
    """Client connection information."""
    
    # Connection identifiers
    connection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    
    # Client information
    client_ip: str            # Client IP
    client_port: int          # Client port
    user_agent: Optional[str] = None  # User agent
    
    # Routing information
    target_service_id: str    # Target service ID
    routing_strategy: str     # Used routing strategy
    routing_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Status information
    status: ConnectionStatus = ConnectionStatus.CONNECTING
    connected_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    
    # Statistics
    bytes_sent: int = 0          # Bytes sent
    bytes_received: int = 0      # Bytes received
    message_count: int = 0       # Message count


class RoutingCondition(BaseModel):
    """Routing condition."""
    
    field: str               # Match field (client_ip, user_agent, etc.)
    operator: ConditionOperator  # Operator
    value: str               # Match value
    case_sensitive: bool = False  # Case sensitive


class RoutingRule(BaseModel):
    """Connection routing rule."""
    
    # Rule identifiers
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                 # Rule name
    priority: int = 100       # Priority (lower number = higher priority)
    enabled: bool = True      # Enabled
    
    # Match conditions
    conditions: List[RoutingCondition] = Field(default_factory=list)
    
    # Routing target
    target_strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    target_services: List[str] = Field(default_factory=list)  # Target service IDs
    target_tags: List[str] = Field(default_factory=list)     # Target service tags
    
    # Advanced configuration
    weight: int = 1           # Weight (for weighted routing)
    fallback_strategy: Optional[RoutingStrategy] = None
    
    # Metadata
    description: str = ""     # Rule description
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CheckResult(BaseModel):
    """Individual check result."""
    
    name: str                 # Check name
    status: HealthStatus      # Check status
    message: str              # Check message
    duration_ms: float        # Check duration (ms)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthCheckResult(BaseModel):
    """Health check result."""
    
    service_id: str           # Service ID
    timestamp: datetime = Field(default_factory=datetime.now)
    status: HealthStatus      # Health status
    response_time_ms: float   # Response time (ms)
    
    # Check details
    checks: Dict[str, CheckResult] = Field(default_factory=dict)
    
    # Error information
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None