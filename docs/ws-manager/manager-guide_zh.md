# MyAgent WebSocket 管理系统完整指南

## 目录

1. [系统概述](#系统概述)
2. [核心组件](#核心组件)
3. [快速开始](#快速开始)
4. [服务管理](#服务管理)
5. [连接路由](#连接路由)
6. [健康监控](#健康监控)
7. [HTTP API](#http-api)
8. [命令行工具](#命令行工具)
9. [最佳实践](#最佳实践)
10. [故障排除](#故障排除)

---

## 系统概述

MyAgent WebSocket 管理系统 (`myagent.manager`) 是一个完整的多智能体服务管理平台，支持在单一管理平台上部署、管理和监控多个 Agent WebSocket 服务实例。

### 主要特性

- ✅ **多服务管理**: 注册、启动、停止、重启多个智能体服务
- ✅ **智能路由**: 5种路由策略（轮询、最少连接、加权随机、哈希、标签）
- ✅ **健康监控**: 自动健康检查和故障恢复
- ✅ **自动重启**: 服务故障自动重启（可配置次数）
- ✅ **HTTP API**: 完整的RESTful API（基于FastAPI）
- ✅ **命令行工具**: 便捷的CLI管理工具
- ✅ **持久化存储**: SQLite数据库存储服务信息
- ✅ **端口管理**: 自动分配和管理服务端口

### 系统架构

```
┌────────────────────────────────────────────────────────────┐
│                   Web UI / CLI / HTTP API                   │
└────────────────────────┬───────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│                     AgentManager                            │
│  ┌───────────────┐ ┌────────────────┐ ┌────────────────┐  │
│  │ ServiceRegistry│ │ConnectionRouter│ │ HealthMonitor  │  │
│  │ (注册中心)     │ │ (路由器)        │ │ (健康监控)     │  │
│  └───────────────┘ └────────────────┘ └────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        ServiceRepository (SQLite数据库)               │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────┘
                         │ 管理
┌────────────────────────▼───────────────────────────────────┐
│                   Agent Services                            │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│  │ Service A  │ │ Service B  │ │ Service C  │   ...        │
│  │ :8081      │ │ :8082      │ │ :8083      │             │
│  └────────────┘ └────────────┘ └────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. AgentManager（中心管理器）

**位置:** `myagent.manager.core.manager.AgentManager`

**功能:** 统一管理所有服务、路由和监控功能。

**初始化:**

```python
from myagent.manager import AgentManager

# 创建管理器
manager = AgentManager(db_path="agent_manager.db")

# 启动管理器
await manager.start(health_check_interval=10)

# 使用上下文管理器（推荐）
async with AgentManager("agent_manager.db") as manager:
    # 管理器自动启动和关闭
    pass
```

**主要方法:**

```python
# 服务管理
await manager.register_service(...)      # 注册服务
await manager.start_service(service_id)  # 启动服务
await manager.stop_service(service_id)   # 停止服务
await manager.restart_service(service_id) # 重启服务
await manager.unregister_service(service_id) # 注销服务

# 批量操作
await manager.start_all_services()       # 启动所有服务
await manager.stop_all_services()        # 停止所有服务

# 查询服务
manager.get_service(service_id)          # 获取服务
manager.get_service_by_name(name)        # 按名称获取
manager.list_services(...)               # 列出服务

# 路由管理
await manager.route_connection(...)      # 路由连接
manager.register_connection(...)         # 注册连接
manager.get_connection_stats()           # 连接统计

# 健康监控
await manager.check_service_health(...)  # 检查服务健康
manager.get_health_summary()             # 健康摘要

# 系统统计
manager.get_system_stats()               # 系统统计信息
```

### 2. ServiceRegistry（服务注册中心）

**位置:** `myagent.manager.core.registry.ServiceRegistry`

**功能:** 管理服务注册、启动、停止和端口分配。

**核心功能:**

- **服务注册**: 验证agent文件、分配端口、保存配置
- **服务启动**: 使用subprocess启动WebSocket服务进程
- **服务停止**: 优雅关闭（10秒超时后强制终止）
- **端口管理**: 自动分配8081-9000范围内的可用端口

**实现细节:**

```python
class ServiceRegistry:
    async def start_service(self, service_id: str) -> bool:
        """启动服务"""
        # 1. 更新状态为STARTING
        # 2. 准备启动命令
        cmd = [
            sys.executable, "-m", "myagent.cli.server", "server",
            agent_path, "--host", host, "--port", port
        ]
        # 3. 启动进程（subprocess.Popen）
        # 4. 等待2秒检查进程状态
        # 5. 更新状态为RUNNING或ERROR
```

### 3. ConnectionRouter（连接路由器）

**位置:** `myagent.manager.core.router.ConnectionRouter`

**功能:** 智能路由客户端连接到合适的服务实例。

**路由策略:**

| 策略 | 描述 | 适用场景 |
|-----|------|---------|
| `ROUND_ROBIN` | 轮询分配 | 负载均衡 |
| `LEAST_CONNECTIONS` | 最少连接优先 | 避免服务过载 |
| `WEIGHTED_RANDOM` | 加权随机（按连接数反向加权） | 负载均衡 |
| `HASH_BASED` | 基于客户端IP的哈希 | 会话亲和性 |
| `TAG_BASED` | 基于服务标签 | 功能分组 |

**路由规则:**

```python
from myagent.manager.storage.models import RoutingRule, RoutingCondition, ConditionOperator

# 创建路由规则
rule = RoutingRule(
    name="mobile_routing",
    priority=100,
    conditions=[
        RoutingCondition(
            field="user_agent",
            operator=ConditionOperator.CONTAINS,
            value="Mobile"
        )
    ],
    target_tags=["mobile"],
    target_strategy=RoutingStrategy.LEAST_CONNECTIONS
)

# 添加路由规则
manager.add_routing_rule(rule)
```

**路由流程:**

```python
async def route_connection(self, client_ip, client_port, **context):
    """
    1. 获取可用服务（RUNNING状态）
    2. 应用路由规则（按优先级）
    3. 匹配条件（user_agent, client_ip, headers等）
    4. 选择目标服务（使用指定策略）
    5. 返回选中的服务
    """
```

### 4. HealthMonitor（健康监控）

**位置:** `myagent.manager.monitoring.health.HealthMonitor`

**功能:** 定期检查服务健康状态并处理故障。

**健康检查项:**

1. **WebSocket连接性** - 尝试连接WebSocket端点
2. **服务状态** - 检查服务是否在RUNNING状态
3. **资源使用** - CPU和内存使用率（可选）

**健康状态:**

```python
class HealthStatus(Enum):
    HEALTHY = "healthy"       # 健康
    UNHEALTHY = "unhealthy"   # 不健康
    DEGRADED = "degraded"     # 降级（部分功能）
    UNKNOWN = "unknown"       # 未知
```

**健康检查结果:**

```python
{
    "service_id": "xxx",
    "status": "healthy",
    "response_time_ms": 45.2,
    "checks": {
        "websocket": {
            "status": "healthy",
            "message": "WebSocket connection successful"
        },
        "status": {
            "status": "healthy",
            "message": "Service is running"
        }
    }
}
```

### 5. ServiceRepository（数据持久化）

**位置:** `myagent.manager.storage.repository.ServiceRepository`

**功能:** SQLite数据库存储和查询服务信息。

**数据表:**

- `services` - 服务信息表
- `routing_rules` - 路由规则表
- `health_checks` - 健康检查历史表

**主要方法:**

```python
repository.save_service(service)           # 保存服务
repository.get_service(service_id)         # 获取服务
repository.list_services(status, tags)     # 查询服务
repository.delete_service(service_id)      # 删除服务
repository.save_routing_rule(rule)         # 保存路由规则
repository.get_routing_rules()             # 获取路由规则
```

### 6. APIServer（HTTP API服务器）

**位置:** `myagent.manager.api.server.APIServer`

**功能:** 基于FastAPI的RESTful API服务器。

**API端点:**

```
GET  /health                    # 健康检查
GET  /api/v1/info              # 系统信息
GET  /api/v1/services          # 列出服务
POST /api/v1/services          # 创建服务
GET  /api/v1/services/{id}     # 获取服务
PUT  /api/v1/services/{id}     # 更新服务
DELETE /api/v1/services/{id}   # 删除服务
POST /api/v1/services/{id}/start   # 启动服务
POST /api/v1/services/{id}/stop    # 停止服务
POST /api/v1/services/{id}/restart # 重启服务
GET  /api/v1/stats             # 系统统计
GET  /api/v1/connections       # 连接列表
```

---

## 快速开始

### 安装和配置

```bash
# 确保已安装MyAgent
pip install -e .

# 或使用uv
uv sync
```

### 1. 创建Agent服务文件

创建一个简单的agent文件 `my_agent.py`:

```python
# my_agent.py
from myagent import create_toolcall_agent
from myagent.tool import BaseTool, ToolResult

class GreetingTool(BaseTool):
    name = "greet"
    description = "打招呼工具"

    async def execute(self, name: str) -> ToolResult:
        return ToolResult(output=f"你好，{name}！")

def create_agent():
    """Agent工厂函数"""
    tools = [GreetingTool()]
    return create_toolcall_agent(
        tools=tools,
        name="greeting_agent",
        description="一个简单的问候智能体"
    )
```

### 2. 使用AgentManager管理服务

```python
# manager_example.py
import asyncio
from myagent.manager import AgentManager

async def main():
    # 创建管理器
    async with AgentManager("manager.db") as manager:
        # 注册服务
        service = await manager.register_service(
            name="greeting_service",
            agent_factory_path="my_agent.py",
            host="localhost",
            port=8081,  # 可选，不指定则自动分配
            description="问候服务",
            tags={"greeting", "demo"},
            auto_start=True  # 自动启动
        )

        if service:
            print(f"服务已注册: {service.name} at {service.endpoint}")

            # 等待服务运行
            await asyncio.sleep(2)

            # 检查服务状态
            stats = manager.get_system_stats()
            print(f"系统状态: {stats}")

            # 保持运行
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 启动管理器

```bash
# 运行管理器示例
uv run python manager_example.py

# 输出:
# 服务已注册: greeting_service at ws://localhost:8081
# 系统状态: {'services': {'total': 1, 'running': 1, ...}, ...}
```

### 4. 连接到服务

```python
# client.py
import asyncio
import websockets
import json

async def test_service():
    uri = "ws://localhost:8081"
    async with websockets.connect(uri) as websocket:
        # 创建会话
        await websocket.send(json.dumps({
            "event": "user.create_session",
            "timestamp": "2024-01-01T00:00:00Z"
        }))

        response = await websocket.recv()
        data = json.loads(response)
        session_id = data.get("session_id")

        # 发送消息
        await websocket.send(json.dumps({
            "session_id": session_id,
            "event": "user.message",
            "content": "使用greet工具问候Alice",
            "timestamp": "2024-01-01T00:00:00Z"
        }))

        # 接收响应
        async for message in websocket:
            data = json.loads(message)
            print(f"收到: {data}")
            if data.get("event") == "agent.final_answer":
                break

asyncio.run(test_service())
```

---

## 服务管理

### 注册服务

```python
from myagent.manager import AgentManager, ServiceConfig

async with AgentManager() as manager:
    # 基础注册
    service = await manager.register_service(
        name="my_service",
        agent_factory_path="/path/to/agent.py",
        host="localhost",
        port=8081
    )

    # 高级配置
    config = ServiceConfig(
        agent_factory_path="/path/to/agent.py",
        max_sessions=100,              # 最大会话数
        session_timeout=1800,          # 会话超时（秒）
        heartbeat_interval=30,         # 心跳间隔
        auto_restart=True,             # 自动重启
        max_restart_count=3,           # 最大重启次数
        restart_delay=5,               # 重启延迟
        health_check_enabled=True,     # 启用健康检查
        health_check_interval=10,      # 健康检查间隔
        environment={                   # 环境变量
            "OPENAI_API_KEY": "sk-xxx"
        }
    )

    service = await manager.register_service(
        name="advanced_service",
        agent_factory_path="/path/to/agent.py",
        tags={"production", "chat"},
        config=config,
        auto_start=True
    )
```

### 启动和停止服务

```python
# 启动单个服务
success = await manager.start_service(service_id)

# 停止单个服务
success = await manager.stop_service(service_id)

# 重启服务
success = await manager.restart_service(service_id)

# 批量启动所有已停止的服务
results = await manager.start_all_services()
# {'service_a': True, 'service_b': True, ...}

# 批量停止所有运行中的服务
results = await manager.stop_all_services()
```

### 查询服务

```python
# 获取单个服务
service = manager.get_service(service_id)
print(f"服务: {service.name}, 状态: {service.status}")

# 按名称获取
service = manager.get_service_by_name("my_service")

# 列出所有服务
all_services = manager.list_services()

# 按状态筛选
running = manager.list_services(status=ServiceStatus.RUNNING)
stopped = manager.list_services(status=ServiceStatus.STOPPED)
error = manager.list_services(status=ServiceStatus.ERROR)

# 按标签筛选
chat_services = manager.list_services(tags=["chat"])

# 分页
services = manager.list_services(limit=10, offset=0)
```

### 服务状态

```python
from myagent.manager.storage.models import ServiceStatus

# 服务状态枚举
ServiceStatus.STOPPED     # 已停止
ServiceStatus.STARTING    # 正在启动
ServiceStatus.RUNNING     # 运行中
ServiceStatus.STOPPING    # 正在停止
ServiceStatus.ERROR       # 错误状态
ServiceStatus.UNHEALTHY   # 运行但不健康

# 检查服务状态
if service.status == ServiceStatus.RUNNING:
    print("服务正在运行")
    print(f"启动时间: {service.started_at}")
    print(f"连接数: {service.stats.active_connections}")
```

### 服务统计信息

```python
# 获取服务统计
service = manager.get_service(service_id)
stats = service.stats

print(f"总连接数: {stats.total_connections}")
print(f"活跃连接: {stats.active_connections}")
print(f"总会话数: {stats.total_sessions}")
print(f"平均响应时间: {stats.avg_response_time}ms")
print(f"错误率: {stats.error_rate}%")
print(f"运行时间: {stats.uptime_seconds}秒")
```

---

## 连接路由

### 路由连接

```python
# 路由新连接
service = await manager.route_connection(
    client_ip="192.168.1.100",
    client_port=54321,
    user_agent="Mozilla/5.0 ...",
    headers={"X-Custom-Header": "value"},
    query_params={"region": "asia"}
)

if service:
    print(f"路由到服务: {service.name}")

    # 注册连接
    connection = manager.register_connection(
        connection_id="conn_123",
        service=service,
        client_ip="192.168.1.100",
        client_port=54321,
        routing_strategy="round_robin"
    )
```

### 配置路由规则

```python
from myagent.manager.storage.models import (
    RoutingRule, RoutingCondition, RoutingStrategy, ConditionOperator
)

# 规则1: 移动设备路由到mobile标签的服务
mobile_rule = RoutingRule(
    name="mobile_routing",
    priority=100,  # 高优先级
    conditions=[
        RoutingCondition(
            field="user_agent",
            operator=ConditionOperator.CONTAINS,
            value="Mobile",
            case_sensitive=False
        )
    ],
    target_tags=["mobile"],
    target_strategy=RoutingStrategy.LEAST_CONNECTIONS,
    enabled=True
)

# 规则2: 特定IP段路由到特定服务
ip_rule = RoutingRule(
    name="internal_routing",
    priority=90,
    conditions=[
        RoutingCondition(
            field="client_ip",
            operator=ConditionOperator.STARTS_WITH,
            value="192.168."
        )
    ],
    target_services=["service_id_1", "service_id_2"],
    target_strategy=RoutingStrategy.HASH_BASED
)

# 规则3: 基于自定义header
header_rule = RoutingRule(
    name="api_version_routing",
    priority=80,
    conditions=[
        RoutingCondition(
            field="X-API-Version",  # 自定义header
            operator=ConditionOperator.EQUALS,
            value="v2"
        )
    ],
    target_tags=["v2"],
    target_strategy=RoutingStrategy.ROUND_ROBIN
)

# 添加规则
manager.add_routing_rule(mobile_rule)
manager.add_routing_rule(ip_rule)
manager.add_routing_rule(header_rule)

# 查询规则
rules = manager.get_routing_rules(enabled_only=True)
```

### 条件操作符

```python
from myagent.manager.storage.models import ConditionOperator

# 所有支持的操作符
ConditionOperator.EQUALS         # 等于
ConditionOperator.NOT_EQUALS     # 不等于
ConditionOperator.CONTAINS       # 包含
ConditionOperator.NOT_CONTAINS   # 不包含
ConditionOperator.STARTS_WITH    # 开始于
ConditionOperator.ENDS_WITH      # 结束于
ConditionOperator.REGEX_MATCH    # 正则匹配
ConditionOperator.IN_LIST        # 在列表中（逗号分隔）
ConditionOperator.NOT_IN_LIST    # 不在列表中

# 示例：正则匹配
regex_condition = RoutingCondition(
    field="user_agent",
    operator=ConditionOperator.REGEX_MATCH,
    value=r"Chrome\/\d+\.\d+",
    case_sensitive=True
)

# 示例：列表匹配
list_condition = RoutingCondition(
    field="region",
    operator=ConditionOperator.IN_LIST,
    value="asia,europe,america"
)
```

### 连接管理

```python
# 获取连接统计
stats = manager.get_connection_stats()
print(stats)
# {
#     "total_connections": 150,
#     "by_status": {
#         "connected": 120,
#         "active": 100,
#         "idle": 20
#     },
#     "by_service": {
#         "service_1": 50,
#         "service_2": 60,
#         "service_3": 40
#     }
# }

# 获取活跃连接列表
connections = manager.get_active_connections()
for conn in connections:
    print(f"连接: {conn.connection_id}")
    print(f"  客户端: {conn.client_ip}:{conn.client_port}")
    print(f"  服务: {conn.target_service_id}")
    print(f"  策略: {conn.routing_strategy}")
    print(f"  状态: {conn.status}")

# 注销连接
manager.unregister_connection(connection_id)
```

---

## 健康监控

### 启动健康监控

```python
async with AgentManager() as manager:
    # 管理器启动时会自动启动健康监控
    # 默认间隔10秒

    # 或手动指定间隔
    await manager.start(health_check_interval=5)  # 5秒检查一次
```

### 检查服务健康

```python
# 检查单个服务
health = await manager.check_service_health(service_id)
print(health)
# {
#     "service_id": "xxx",
#     "status": "healthy",
#     "response_time_ms": 45.2,
#     "timestamp": "2024-01-01T12:00:00Z",
#     "checks": {
#         "websocket": {...},
#         "status": {...},
#         "resources": {...}
#     }
# }

# 检查所有服务
results = await manager.check_all_services_health()
for service_id, health in results.items():
    print(f"{service_id}: {health['status']}")
```

### 健康摘要

```python
# 获取整体健康摘要
summary = manager.get_health_summary()
print(summary)
# {
#     "total_services": 10,
#     "healthy": 8,
#     "unhealthy": 1,
#     "degraded": 0,
#     "unknown": 1,
#     "last_check": "2024-01-01T12:00:00Z"
# }
```

### 健康历史

```python
# 获取服务的健康检查历史
history = manager.get_service_health_history(service_id, limit=10)
for record in history:
    print(f"{record.timestamp}: {record.status} ({record.response_time_ms}ms)")
```

### 自动重启

```python
# 配置自动重启
config = ServiceConfig(
    agent_factory_path="agent.py",
    auto_restart=True,          # 启用自动重启
    max_restart_count=3,        # 最多重启3次
    restart_delay=5             # 重启前等待5秒
)

service = await manager.register_service(
    name="auto_restart_service",
    agent_factory_path="agent.py",
    config=config
)

# 管理器会自动监控服务状态
# 如果服务进入ERROR或UNHEALTHY状态，且重启次数未达上限
# 会自动重启服务
```

---

## HTTP API

### 启动API服务器

```python
from myagent.manager import AgentManager, APIServer
import uvicorn

async def main():
    # 创建管理器
    manager = AgentManager("manager.db")
    await manager.start()

    # 创建API服务器
    api_server = APIServer(manager)

    # 启动API服务器
    config = uvicorn.Config(
        api_server.app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()
```

或使用CLI：

```bash
# 启动管理器API服务器
myagent-manager api --port 8000

# 或使用完整路径
uv run python -m myagent.manager.cli api --port 8000
```

### API端点文档

启动后访问：
- **API文档**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要API端点

#### 系统信息

```bash
# 健康检查
curl http://localhost:8000/health

# 系统信息
curl http://localhost:8000/api/v1/info

# 系统统计
curl http://localhost:8000/api/v1/stats
```

#### 服务管理

```bash
# 创建服务
curl -X POST http://localhost:8000/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_service",
    "agent_factory_path": "/path/to/agent.py",
    "host": "localhost",
    "port": 8081,
    "tags": ["production"],
    "auto_start": true
  }'

# 列出所有服务
curl http://localhost:8000/api/v1/services

# 按状态筛选
curl "http://localhost:8000/api/v1/services?status=running"

# 按标签筛选
curl "http://localhost:8000/api/v1/services?tags=production,chat"

# 获取服务详情
curl http://localhost:8000/api/v1/services/{service_id}

# 启动服务
curl -X POST http://localhost:8000/api/v1/services/{service_id}/start

# 停止服务
curl -X POST http://localhost:8000/api/v1/services/{service_id}/stop

# 重启服务
curl -X POST http://localhost:8000/api/v1/services/{service_id}/restart

# 删除服务
curl -X DELETE http://localhost:8000/api/v1/services/{service_id}
```

#### 健康检查

```bash
# 检查所有服务健康
curl http://localhost:8000/api/v1/health

# 检查特定服务
curl http://localhost:8000/api/v1/services/{service_id}/health

# 健康历史
curl http://localhost:8000/api/v1/services/{service_id}/health/history
```

#### 连接管理

```bash
# 获取所有连接
curl http://localhost:8000/api/v1/connections

# 获取服务的连接
curl http://localhost:8000/api/v1/services/{service_id}/connections

# 连接统计
curl http://localhost:8000/api/v1/connections/stats
```

---

## 命令行工具

### 管理器CLI

```bash
# 查看所有命令
myagent-manager --help

# 或使用完整模块路径
uv run python -m myagent.manager.cli --help

# 启动守护进程
myagent-manager daemon

# 启动API服务器
myagent-manager api --port 8000
```

### 服务操作CLI

```bash
# 注册服务
myagent-manager register my_service /path/to/agent.py \
  --host localhost \
  --port 8081 \
  --tags production,chat \
  --auto-start

# 启动服务
myagent-manager start my_service

# 停止服务
myagent-manager stop my_service

# 重启服务
myagent-manager restart my_service

# 列出所有服务
myagent-manager list

# 按状态筛选
myagent-manager list --status running

# 查看服务详情
myagent-manager status my_service

# 查看系统统计
myagent-manager stats

# 注销服务
myagent-manager unregister my_service
```

---

## 最佳实践

### 1. 服务配置

```python
# 生产环境推荐配置
production_config = ServiceConfig(
    agent_factory_path="agent.py",
    max_sessions=100,               # 限制最大会话数
    session_timeout=1800,           # 30分钟超时
    heartbeat_interval=30,          # 心跳检测
    auto_restart=True,              # 启用自动重启
    max_restart_count=3,            # 限制重启次数
    restart_delay=10,               # 重启前等待10秒
    health_check_enabled=True,      # 启用健康检查
    health_check_interval=10,       # 10秒检查一次
    environment={
        "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        "LOG_LEVEL": "INFO"
    }
)
```

### 2. 端口管理

```python
# 让管理器自动分配端口（推荐）
service = await manager.register_service(
    name="auto_port_service",
    agent_factory_path="agent.py",
    # port 参数省略，自动分配8081-9000范围内的端口
)

# 手动指定端口
service = await manager.register_service(
    name="manual_port_service",
    agent_factory_path="agent.py",
    port=8888  # 确保端口可用
)
```

### 3. 标签管理

```python
# 使用有意义的标签组织服务
service = await manager.register_service(
    name="chat_service_v2",
    agent_factory_path="chat_agent.py",
    tags={
        "production",      # 环境标签
        "chat",           # 功能标签
        "v2",             # 版本标签
        "asia-east"       # 区域标签
    }
)

# 通过标签查询
chat_services = manager.list_services(tags=["chat"])
v2_services = manager.list_services(tags=["v2"])
prod_chat = manager.list_services(tags=["production", "chat"])
```

### 4. 错误处理

```python
try:
    service = await manager.register_service(...)
    if service:
        logger.info(f"服务注册成功: {service.name}")
    else:
        logger.error("服务注册失败")
except Exception as e:
    logger.error(f"注册服务时出错: {e}")

# 检查服务状态
service = manager.get_service(service_id)
if service.status == ServiceStatus.ERROR:
    logger.error(f"服务错误: {service.error_message}")
    # 尝试重启
    await manager.restart_service(service_id)
```

### 5. 监控和日志

```python
# 定期检查系统状态
async def monitor_system():
    while True:
        stats = manager.get_system_stats()
        logger.info(f"系统状态: {stats}")

        # 检查不健康的服务
        unhealthy = manager.list_services(status=ServiceStatus.UNHEALTHY)
        for service in unhealthy:
            logger.warning(f"服务不健康: {service.name}")
            # 发送告警

        await asyncio.sleep(60)  # 每分钟检查一次
```

### 6. 优雅关闭

```python
async def main():
    manager = AgentManager()
    try:
        await manager.start()
        # 运行主逻辑
        await run_forever()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        # 停止所有服务
        await manager.stop_all_services()
        # 关闭管理器
        await manager.stop()
        logger.info("管理器已关闭")
```

---

## 故障排除

### 常见问题

#### 1. 服务启动失败

**问题:** 服务状态为ERROR

**解决方案:**

```python
# 检查错误信息
service = manager.get_service(service_id)
print(f"错误: {service.error_message}")

# 常见原因:
# - Agent文件不存在或路径错误
# - 端口被占用
# - Python环境问题
# - 依赖包缺失

# 检查agent文件
from pathlib import Path
if not Path(service.config.agent_factory_path).exists():
    print("Agent文件不存在")

# 检查端口
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', service.port))
    s.close()
    print("端口可用")
except OSError:
    print("端口被占用")
```

#### 2. 健康检查失败

**问题:** 服务UNHEALTHY

**解决方案:**

```python
# 检查健康检查详情
health = await manager.check_service_health(service_id)
print(health)

# 检查WebSocket连接
import websockets
try:
    async with websockets.connect(service.endpoint, timeout=5):
        print("WebSocket连接成功")
except Exception as e:
    print(f"WebSocket连接失败: {e}")

# 重启服务
await manager.restart_service(service_id)
```

#### 3. 路由不工作

**问题:** 连接路由到错误的服务

**解决方案:**

```python
# 检查路由规则
rules = manager.get_routing_rules()
for rule in rules:
    print(f"规则: {rule.name}, 优先级: {rule.priority}")
    print(f"  条件: {rule.conditions}")
    print(f"  目标: tags={rule.target_tags}, services={rule.target_services}")

# 测试路由
service = await manager.route_connection(
    client_ip="192.168.1.100",
    client_port=12345,
    user_agent="test"
)
print(f"路由到: {service.name if service else 'None'}")

# 检查可用服务
available = manager.list_services(status=ServiceStatus.RUNNING)
print(f"可用服务: {[s.name for s in available]}")
```

#### 4. 数据库锁定

**问题:** SQLite database is locked

**解决方案:**

```python
# 确保正确关闭管理器
async with AgentManager("manager.db") as manager:
    # 使用上下文管理器确保资源释放
    pass

# 或检查是否有其他进程在使用数据库
import sqlite3
try:
    conn = sqlite3.connect("manager.db", timeout=1.0)
    conn.close()
    print("数据库可访问")
except sqlite3.OperationalError as e:
    print(f"数据库访问错误: {e}")
```

### 调试技巧

1. **启用详细日志**

```python
from myagent.logger import logger
import logging

logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
)
```

2. **检查进程状态**

```bash
# 查看运行中的服务进程
ps aux | grep "myagent.cli.server"

# 查看端口占用
lsof -i :8081
netstat -an | grep 8081
```

3. **测试WebSocket连接**

```bash
# 使用wscat测试
npm install -g wscat
wscat -c ws://localhost:8081
```

4. **查看数据库内容**

```bash
# 使用sqlite3查看数据库
sqlite3 manager.db

# 查看服务表
SELECT * FROM services;

# 查看路由规则
SELECT * FROM routing_rules;
```

---

## 总结

MyAgent WebSocket管理系统提供了完整的多智能体服务管理解决方案:

- ✅ **易用性**: 简单的API和CLI工具
- ✅ **可靠性**: 自动健康检查和故障恢复
- ✅ **灵活性**: 多种路由策略和配置选项
- ✅ **可扩展性**: 支持管理大量并发服务
- ✅ **可观测性**: 完整的监控和统计功能

通过本指南，您应该能够：

1. 理解管理系统的核心组件
2. 注册和管理多个Agent服务
3. 配置智能路由规则
4. 监控服务健康状态
5. 使用HTTP API和CLI工具
6. 解决常见问题

## 相关文档

- [数据模型](./data-models.md) - 完整的数据模型定义
- [API设计](./api-design.md) - HTTP API详细文档
- [路由策略](./routing-strategies.md) - 路由策略详解
- [部署架构](./deployment-architecture.md) - 生产部署指南

## 获取帮助

如有问题，请：

1. 查看[故障排除](#故障排除)章节
2. 检查系统日志
3. 在GitHub Issues提出问题
