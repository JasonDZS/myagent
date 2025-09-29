# API 设计

## 1. HTTP 管理 API

### 基础路径: `/api/v1`

### 1.1 服务管理 API

#### 注册智能体服务
```http
POST /services
Content-Type: application/json

{
    "name": "weather-agent",
    "description": "Weather information agent",
    "agent_factory_path": "./agents/weather_agent.py",
    "host": "localhost",
    "port": 8081,
    "tags": ["weather", "information"],
    "config": {
        "max_sessions": 100,
        "session_timeout": 1800,
        "auto_restart": true,
        "health_check_enabled": true
    }
}
```

**响应:**
```json
{
    "success": true,
    "service_id": "uuid-string",
    "message": "Service registered successfully",
    "endpoint": "ws://localhost:8081"
}
```

#### 获取服务列表
```http
GET /services?tag=weather&status=running&limit=10&offset=0
```

**响应:**
```json
{
    "services": [
        {
            "service_id": "uuid-string",
            "name": "weather-agent",
            "description": "Weather information agent",
            "host": "localhost",
            "port": 8081,
            "endpoint": "ws://localhost:8081",
            "status": "running",
            "tags": ["weather", "information"],
            "created_at": "2024-01-01T10:00:00Z",
            "started_at": "2024-01-01T10:01:00Z",
            "stats": {
                "total_connections": 15,
                "active_sessions": 8,
                "uptime_seconds": 3600
            }
        }
    ],
    "total": 1,
    "page": {
        "limit": 10,
        "offset": 0,
        "has_next": false
    }
}
```

#### 获取服务详情
```http
GET /services/{service_id}
```

**响应:**
```json
{
    "service_id": "uuid-string",
    "name": "weather-agent",
    "description": "Weather information agent",
    "host": "localhost",
    "port": 8081,
    "endpoint": "ws://localhost:8081",
    "status": "running",
    "tags": ["weather", "information"],
    "config": {
        "max_sessions": 100,
        "session_timeout": 1800,
        "auto_restart": true,
        "health_check_enabled": true
    },
    "stats": {
        "total_connections": 15,
        "active_connections": 12,
        "peak_connections": 25,
        "total_sessions": 45,
        "active_sessions": 8,
        "completed_sessions": 37,
        "avg_session_duration": 300.5,
        "memory_usage_mb": 128.5,
        "cpu_usage_percent": 15.2,
        "error_count": 2,
        "error_rate": 0.04
    },
    "health": {
        "status": "healthy",
        "last_check": "2024-01-01T10:30:00Z",
        "response_time_ms": 5.2
    }
}
```

#### 启动服务
```http
POST /services/{service_id}/start
```

#### 停止服务
```http
POST /services/{service_id}/stop
```

#### 重启服务
```http
POST /services/{service_id}/restart
```

#### 更新服务配置
```http
PUT /services/{service_id}/config
Content-Type: application/json

{
    "max_sessions": 200,
    "auto_restart": false
}
```

#### 删除服务
```http
DELETE /services/{service_id}
```

### 1.2 连接管理 API

#### 获取活跃连接
```http
GET /connections?service_id=uuid&status=active&limit=20
```

**响应:**
```json
{
    "connections": [
        {
            "connection_id": "conn-uuid",
            "session_id": "session-uuid",
            "client_ip": "192.168.1.100",
            "target_service_id": "service-uuid",
            "status": "active",
            "connected_at": "2024-01-01T10:15:00Z",
            "last_activity": "2024-01-01T10:29:00Z",
            "bytes_sent": 1024,
            "bytes_received": 2048,
            "message_count": 15
        }
    ],
    "total": 1
}
```

#### 断开连接
```http
POST /connections/{connection_id}/disconnect
Content-Type: application/json

{
    "reason": "Administrative disconnect",
    "notify_client": true
}
```

### 1.3 路由管理 API

#### 创建路由规则
```http
POST /routing/rules
Content-Type: application/json

{
    "name": "VIP用户路由",
    "priority": 10,
    "conditions": [
        {
            "field": "header.x-user-tier",
            "operator": "equals",
            "value": "vip"
        }
    ],
    "target_strategy": "least_connections",
    "target_tags": ["high-performance"],
    "enabled": true
}
```

#### 获取路由规则
```http
GET /routing/rules?enabled=true
```

#### 更新路由规则
```http
PUT /routing/rules/{rule_id}
```

#### 删除路由规则
```http
DELETE /routing/rules/{rule_id}
```

### 1.4 监控统计 API

#### 获取总体统计
```http
GET /stats/overview
```

**响应:**
```json
{
    "services": {
        "total": 5,
        "running": 4,
        "stopped": 1,
        "error": 0
    },
    "connections": {
        "total": 150,
        "active": 120,
        "peak_today": 200
    },
    "sessions": {
        "total_today": 350,
        "active": 85,
        "completed_today": 265
    },
    "performance": {
        "avg_response_time_ms": 45.2,
        "throughput_per_minute": 125.5,
        "error_rate": 0.02
    },
    "resources": {
        "total_memory_mb": 1024.5,
        "total_cpu_percent": 35.2
    }
}
```

#### 获取时间序列数据
```http
GET /stats/timeseries?metric=connections&period=1h&interval=5m&service_id=uuid
```

**响应:**
```json
{
    "metric": "connections",
    "period": "1h",
    "interval": "5m",
    "data": [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "value": 45
        },
        {
            "timestamp": "2024-01-01T10:05:00Z", 
            "value": 52
        }
    ]
}
```

### 1.5 健康检查 API

#### 获取服务健康状态
```http
GET /health/services/{service_id}
```

#### 手动执行健康检查
```http
POST /health/services/{service_id}/check
```

#### 获取健康检查历史
```http
GET /health/services/{service_id}/history?limit=50
```

### 1.6 日志 API

#### 获取服务日志
```http
GET /logs/services/{service_id}?level=info&limit=100&since=2024-01-01T10:00:00Z
```

#### 搜索日志
```http
GET /logs/search?query=error&service_id=uuid&limit=50
```

## 2. WebSocket 代理协议

### 2.1 连接建立

客户端连接到管理系统的 WebSocket 端点，管理系统根据路由规则转发到具体的智能体服务。

#### 连接端点
```
ws://manager-host:manager-port/ws
```

#### 连接参数 (通过查询字符串或头部)
```
?service=weather-agent          # 指定服务名称
?tag=weather                    # 通过标签路由
?session_id=existing-session    # 恢复已有会话
&routing_hint=least_connections # 路由提示
```

### 2.2 代理消息格式

管理系统在客户端和智能体服务之间透明代理 WebSocket 消息，同时添加管理元数据。

#### 管理系统添加的消息头
```json
{
    "proxy_metadata": {
        "connection_id": "conn-uuid",
        "target_service": "weather-agent", 
        "routing_strategy": "least_connections",
        "timestamp": "2024-01-01T10:30:00Z"
    },
    "original_message": {
        // 原始客户端消息
    }
}
```

### 2.3 管理事件

管理系统会发送特殊的管理事件给客户端:

#### 连接路由事件
```json
{
    "event": "connection_routed",
    "data": {
        "target_service": "weather-agent",
        "service_endpoint": "ws://localhost:8081",
        "routing_strategy": "least_connections"
    }
}
```

#### 服务切换事件 (故障转移)
```json
{
    "event": "service_switched", 
    "data": {
        "from_service": "weather-agent-1",
        "to_service": "weather-agent-2", 
        "reason": "service_unhealthy",
        "session_preserved": true
    }
}
```

#### 管理通知
```json
{
    "event": "management_notification",
    "data": {
        "type": "maintenance_window",
        "message": "Service will be restarted in 5 minutes",
        "severity": "warning",
        "countdown_seconds": 300
    }
}
```

## 3. CLI 命令行接口

### 3.1 服务管理命令

```bash
# 注册服务
myagent-manager register weather-agent ./agents/weather_agent.py \
    --port 8081 --tags weather,info --max-sessions 100

# 启动服务
myagent-manager start weather-agent

# 停止服务  
myagent-manager stop weather-agent

# 重启服务
myagent-manager restart weather-agent

# 列出服务
myagent-manager list --tag weather --status running

# 查看服务详情
myagent-manager show weather-agent

# 删除服务
myagent-manager remove weather-agent
```

### 3.2 监控命令

```bash
# 查看总体状态
myagent-manager status

# 实时监控
myagent-manager monitor --service weather-agent --interval 5

# 查看日志
myagent-manager logs weather-agent --follow --level error

# 健康检查
myagent-manager health-check weather-agent
```

### 3.3 连接管理命令

```bash
# 查看活跃连接
myagent-manager connections --service weather-agent

# 断开连接
myagent-manager disconnect {connection_id} --reason "maintenance"
```

### 3.4 路由管理命令

```bash
# 创建路由规则
myagent-manager route create vip-routing \
    --condition "header.x-user-tier=vip" \
    --target-tag high-performance \
    --strategy least_connections

# 列出路由规则
myagent-manager route list

# 删除路由规则  
myagent-manager route delete vip-routing
```

## 4. 错误处理

### 4.1 HTTP API 错误格式

```json
{
    "success": false,
    "error": {
        "code": "SERVICE_NOT_FOUND",
        "message": "Service with ID 'uuid' not found",
        "details": {
            "service_id": "uuid",
            "timestamp": "2024-01-01T10:30:00Z"
        }
    }
}
```

### 4.2 常见错误码

- `INVALID_REQUEST`: 请求参数无效
- `SERVICE_NOT_FOUND`: 服务不存在
- `SERVICE_ALREADY_EXISTS`: 服务名称已存在
- `SERVICE_START_FAILED`: 服务启动失败
- `PORT_IN_USE`: 端口已被占用
- `INSUFFICIENT_RESOURCES`: 资源不足
- `ROUTING_FAILED`: 路由失败
- `CONNECTION_NOT_FOUND`: 连接不存在
- `HEALTH_CHECK_FAILED`: 健康检查失败

### 4.3 WebSocket 错误消息

```json
{
    "event": "error",
    "data": {
        "code": "ROUTING_FAILED",
        "message": "No healthy service available for routing",
        "recoverable": false
    }
}
```