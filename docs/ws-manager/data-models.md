# 数据模型设计

## 核心数据模型

### 1. AgentService (智能体服务)

```python
class AgentService:
    """智能体服务实例"""
    
    # 基本信息
    service_id: str              # 唯一服务ID (UUID)
    name: str                    # 服务名称 (唯一)
    description: str             # 服务描述
    
    # 网络配置
    host: str                    # 服务主机地址
    port: int                    # 服务端口
    endpoint: str                # WebSocket 端点 (ws://host:port)
    
    # 元数据
    tags: Set[str]               # 服务标签 (用于路由和过滤)
    agent_type: str              # 智能体类型 (react, toolcall, custom)
    version: str                 # 服务版本
    
    # 状态信息
    status: ServiceStatus        # 服务状态
    created_at: datetime         # 创建时间
    started_at: Optional[datetime]  # 启动时间
    last_health_check: Optional[datetime]  # 最后健康检查时间
    
    # 错误信息
    error_message: Optional[str] # 错误消息
    restart_count: int          # 重启次数
    
    # 配置
    config: ServiceConfig       # 服务配置
    
    # 运行时统计
    stats: ServiceStats         # 服务统计信息
```

### 2. ServiceStatus (服务状态)

```python
class ServiceStatus(str, Enum):
    """服务状态枚举"""
    
    STOPPED = "stopped"         # 已停止
    STARTING = "starting"       # 启动中
    RUNNING = "running"         # 运行中
    STOPPING = "stopping"       # 停止中
    ERROR = "error"            # 错误状态
    UNHEALTHY = "unhealthy"    # 不健康 (运行但响应异常)
```

### 3. ServiceConfig (服务配置)

```python
class ServiceConfig:
    """服务配置"""
    
    # 智能体工厂
    agent_factory_path: str     # 智能体工厂文件路径
    
    # 服务参数
    max_sessions: int          # 最大会话数 (0=无限制)
    session_timeout: int       # 会话超时时间 (秒)
    heartbeat_interval: int    # 心跳间隔 (秒)
    
    # 资源限制
    memory_limit_mb: Optional[int]  # 内存限制 (MB)
    cpu_limit_percent: Optional[int]  # CPU使用限制 (%)
    
    # 自动重启
    auto_restart: bool         # 是否自动重启
    max_restart_count: int     # 最大重启次数
    restart_delay: int         # 重启延迟 (秒)
    
    # 健康检查
    health_check_enabled: bool # 是否启用健康检查
    health_check_interval: int # 健康检查间隔 (秒)
    health_check_timeout: int  # 健康检查超时 (秒)
    
    # 环境变量
    environment: Dict[str, str] # 环境变量
```

### 4. ServiceStats (服务统计)

```python
class ServiceStats:
    """服务统计信息"""
    
    # 连接统计
    total_connections: int      # 总连接数
    active_connections: int     # 活跃连接数
    peak_connections: int       # 峰值连接数
    
    # 会话统计  
    total_sessions: int         # 总会话数
    active_sessions: int        # 活跃会话数
    completed_sessions: int     # 完成的会话数
    failed_sessions: int        # 失败的会话数
    
    # 性能指标
    avg_session_duration: float # 平均会话时长 (秒)
    avg_response_time: float    # 平均响应时间 (毫秒)
    throughput_per_minute: float # 每分钟处理请求数
    
    # 资源使用
    memory_usage_mb: float      # 内存使用量 (MB)
    cpu_usage_percent: float    # CPU使用率 (%)
    
    # 错误统计
    error_count: int           # 错误总数
    error_rate: float          # 错误率 (%)
    
    # 时间戳
    last_updated: datetime     # 最后更新时间
    uptime_seconds: int        # 运行时长 (秒)
```

### 5. ConnectionInfo (连接信息)

```python
class ConnectionInfo:
    """客户端连接信息"""
    
    # 连接标识
    connection_id: str         # 连接ID
    session_id: Optional[str]  # 会话ID (如果已创建会话)
    
    # 客户端信息
    client_ip: str            # 客户端IP
    client_port: int          # 客户端端口  
    user_agent: Optional[str] # 用户代理
    
    # 路由信息
    target_service_id: str    # 目标服务ID
    routing_strategy: str     # 使用的路由策略
    routing_metadata: Dict[str, Any]  # 路由元数据
    
    # 状态信息
    status: ConnectionStatus  # 连接状态
    connected_at: datetime    # 连接时间
    last_activity: datetime   # 最后活动时间
    
    # 统计信息
    bytes_sent: int          # 发送字节数
    bytes_received: int      # 接收字节数
    message_count: int       # 消息数量
```

### 6. ConnectionStatus (连接状态)

```python
class ConnectionStatus(str, Enum):
    """连接状态枚举"""
    
    CONNECTING = "connecting"   # 连接中
    CONNECTED = "connected"     # 已连接
    ACTIVE = "active"          # 活跃 (有会话)
    IDLE = "idle"              # 空闲
    DISCONNECTING = "disconnecting"  # 断开连接中
    DISCONNECTED = "disconnected"    # 已断开
    ERROR = "error"            # 错误状态
```

### 7. RoutingRule (路由规则)

```python
class RoutingRule:
    """连接路由规则"""
    
    # 规则标识
    rule_id: str              # 规则ID
    name: str                 # 规则名称
    priority: int             # 优先级 (数字越小优先级越高)
    enabled: bool             # 是否启用
    
    # 匹配条件
    conditions: List[RoutingCondition]  # 匹配条件列表
    
    # 路由目标
    target_strategy: RoutingStrategy    # 路由策略
    target_services: List[str]          # 目标服务列表 (service_id)
    target_tags: List[str]             # 目标服务标签
    
    # 高级配置
    weight: int               # 权重 (用于加权路由)
    fallback_strategy: Optional[RoutingStrategy]  # 备用策略
    
    # 元数据
    description: str          # 规则描述
    created_at: datetime      # 创建时间
    updated_at: datetime      # 更新时间
```

### 8. RoutingCondition (路由条件)

```python
class RoutingCondition:
    """路由匹配条件"""
    
    field: str               # 匹配字段 (client_ip, user_agent, header, etc.)
    operator: ConditionOperator  # 操作符
    value: str               # 匹配值
    case_sensitive: bool     # 是否区分大小写
```

### 9. RoutingStrategy (路由策略)

```python
class RoutingStrategy(str, Enum):
    """路由策略枚举"""
    
    ROUND_ROBIN = "round_robin"           # 轮询
    LEAST_CONNECTIONS = "least_connections"  # 最少连接
    WEIGHTED_RANDOM = "weighted_random"    # 加权随机
    HASH_BASED = "hash_based"             # 基于哈希
    TAG_BASED = "tag_based"               # 基于标签
    MANUAL = "manual"                     # 手动指定
```

### 10. ConditionOperator (条件操作符)

```python
class ConditionOperator(str, Enum):
    """路由条件操作符"""
    
    EQUALS = "equals"           # 等于
    NOT_EQUALS = "not_equals"   # 不等于
    CONTAINS = "contains"       # 包含
    NOT_CONTAINS = "not_contains"  # 不包含
    STARTS_WITH = "starts_with"    # 开始于
    ENDS_WITH = "ends_with"        # 结束于
    REGEX_MATCH = "regex_match"    # 正则匹配
    IN_LIST = "in_list"            # 在列表中
    NOT_IN_LIST = "not_in_list"    # 不在列表中
```

### 11. HealthCheckResult (健康检查结果)

```python
class HealthCheckResult:
    """健康检查结果"""
    
    service_id: str           # 服务ID
    timestamp: datetime       # 检查时间
    status: HealthStatus      # 健康状态
    response_time_ms: float   # 响应时间 (毫秒)
    
    # 检查详情
    checks: Dict[str, CheckResult]  # 各项检查结果
    
    # 错误信息
    error_message: Optional[str]    # 错误消息
    error_details: Optional[Dict[str, Any]]  # 错误详情
```

### 12. HealthStatus (健康状态)

```python
class HealthStatus(str, Enum):
    """健康检查状态"""
    
    HEALTHY = "healthy"       # 健康
    UNHEALTHY = "unhealthy"   # 不健康
    DEGRADED = "degraded"     # 降级 (部分功能异常)
    UNKNOWN = "unknown"       # 未知 (无法检查)
```

### 13. CheckResult (检查项结果)

```python
class CheckResult:
    """单项检查结果"""
    
    name: str                 # 检查项名称
    status: HealthStatus      # 检查状态
    message: str              # 检查消息
    duration_ms: float        # 检查耗时 (毫秒)
    metadata: Dict[str, Any]  # 额外元数据
```

## 数据关系

```
AgentService (1) -----> (1) ServiceConfig
             (1) -----> (1) ServiceStats
             (1) -----> (N) ConnectionInfo
             (1) -----> (N) HealthCheckResult

RoutingRule (1) -----> (N) RoutingCondition
            (N) -----> (N) AgentService (通过 target_services)

ConnectionInfo (N) -----> (1) AgentService
               (1) -----> (1) RoutingRule (使用的规则)

HealthCheckResult (N) -----> (1) AgentService
                  (1) -----> (N) CheckResult
```

## 数据存储

### SQLite 本地存储
- 服务注册信息 (AgentService, ServiceConfig)
- 路由规则 (RoutingRule, RoutingCondition)  
- 历史统计数据
- 健康检查历史

### 内存缓存
- 实时连接信息 (ConnectionInfo)
- 当前服务统计 (ServiceStats)
- 最新健康检查结果

### 可选 Redis 存储 (分布式部署)
- 分布式会话状态
- 跨节点服务发现
- 实时统计数据同步