# MyAgent WebSocket 管理系统使用指南

本指南介绍如何使用 MyAgent WebSocket 管理系统来部署和管理多个智能体服务。

## 系统概览

MyAgent WebSocket 管理系统提供以下核心功能：

- **多服务管理**: 注册、启动、停止、重启多个智能体服务
- **智能路由**: 自动将客户端连接路由到合适的服务实例
- **健康监控**: 实时监控服务健康状态和性能指标
- **CLI 工具**: 命令行管理工具
- **代理服务器**: 统一的 WebSocket 入口
- **负载均衡**: 多种路由策略支持

## 快速开始

### 1. 安装依赖

确保已安装所需的依赖包：

```bash
# 安装 websockets (如果还没有)
pip install websockets rich click
```

### 2. 准备智能体文件

创建一个智能体文件，例如 `my_agent.py`：

```python
from myagent import create_react_agent
from myagent.tool import BaseTool, ToolResult

class EchoTool(BaseTool):
    name: str = "echo"
    description: str = "Echo back a message"
    
    async def execute(self, message: str) -> ToolResult:
        return ToolResult(
            success=True,
            content=f"Echo: {message}"
        )

def create_agent():
    return create_react_agent(
        name="echo-agent",
        tools=[EchoTool()],
        system_prompt="You are an echo agent.",
    )
```

### 3. 注册和启动服务

```bash
# 注册服务
python -m myagent.manager.cli.manager register my-echo-agent my_agent.py \\
    --description "My echo agent" \\
    --tags "echo,demo" \\
    --auto-start

# 查看服务列表
python -m myagent.manager.cli.manager list

# 检查服务状态
python -m myagent.manager.cli.manager status my-echo-agent
```

### 4. 启动服务器

有两种方式启动服务器：

#### 选项 A: 启动代理服务器（WebSocket 入口）

```bash
# 启动代理服务器 (在新终端窗口中)
python -m myagent.manager.cli.proxy --host localhost --port 9090
```

#### 选项 B: 启动 HTTP API 服务器

```bash
# 启动 HTTP API 服务器
python -m myagent.manager.cli.api --host localhost --port 8080

# 同时启动 HTTP API 和 WebSocket 代理
python -m myagent.manager.cli.api --host localhost --port 8080 --proxy-port 9090
```

### 5. 连接和使用

#### WebSocket 客户端连接

客户端可以连接到 `ws://localhost:9090`，连接会自动路由到可用的智能体服务。

#### HTTP API 访问

- **API 文档**: http://localhost:8080/docs
- **API 基础地址**: http://localhost:8080/api/v1
- **健康检查**: http://localhost:8080/health

## 命令行工具详解

### 服务管理命令

#### 注册服务

```bash
python -m myagent.manager.cli.manager register <service-name> <agent-file> [options]
```

选项：
- `--host`: 服务主机 (默认: localhost)
- `--port`: 服务端口 (自动分配)
- `--description`: 服务描述
- `--tags`: 标签 (逗号分隔)
- `--auto-start`: 注册后自动启动
- `--max-sessions`: 最大会话数
- `--session-timeout`: 会话超时时间
- `--auto-restart`: 启用自动重启

#### 服务控制

```bash
# 启动服务
python -m myagent.manager.cli.manager start <service-name>

# 停止服务
python -m myagent.manager.cli.manager stop <service-name>

# 重启服务
python -m myagent.manager.cli.manager restart <service-name>

# 取消注册服务
python -m myagent.manager.cli.manager unregister <service-name>
```

#### 查看信息

```bash
# 列出所有服务
python -m myagent.manager.cli.manager list

# 按状态过滤
python -m myagent.manager.cli.manager list --status running

# 按标签过滤
python -m myagent.manager.cli.manager list --tags weather

# 查看详细状态
python -m myagent.manager.cli.manager status <service-name>

# 查看系统统计
python -m myagent.manager.cli.manager stats
```

#### 守护进程模式

```bash
# 运行管理器守护进程
python -m myagent.manager.cli.manager daemon --interval 10
```

### 代理服务器

```bash
# 启动代理服务器
python -m myagent.manager.cli.proxy \\
    --host localhost \\
    --port 9090 \\
    --db-path agent_manager.db \\
    --health-interval 10
```

### HTTP API 服务器

```bash
# 启动 API 服务器
python -m myagent.manager.cli.api \\
    --host localhost \\
    --port 8080 \\
    --db-path agent_manager.db \\
    --health-interval 10

# 同时启动 API 和代理服务器
python -m myagent.manager.cli.api \\
    --host localhost \\
    --port 8080 \\
    --proxy-port 9090 \\
    --db-path agent_manager.db \\
    --health-interval 10
```

## 编程接口

### 使用 Python API

```python
import asyncio
from myagent.manager import AgentManager
from myagent.manager.storage.models import ServiceConfig

async def main():
    # 创建管理器
    manager = AgentManager("my_manager.db")
    
    try:
        # 启动管理器
        await manager.start()
        
        # 注册服务
        config = ServiceConfig(
            agent_factory_path="my_agent.py",
            max_sessions=10,
            auto_restart=True,
        )
        
        service = await manager.register_service(
            name="my-service",
            agent_factory_path="my_agent.py",
            description="My test service",
            tags={"demo"},
            config=config,
            auto_start=True,
        )
        
        # 检查健康状态
        health = await manager.check_service_health(service.service_id)
        print(f"Service health: {health.status}")
        
        # 获取统计信息
        stats = manager.get_system_stats()
        print(f"Running services: {stats['services']['running']}")
        
    finally:
        await manager.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 使用 HTTP API

#### curl 示例

```bash
# 获取系统信息
curl http://localhost:8080/api/v1/info

# 列出所有服务
curl http://localhost:8080/api/v1/services

# 创建新服务
curl -X POST http://localhost:8080/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-service",
    "agent_factory_path": "./my_agent.py",
    "description": "My test service",
    "tags": ["test"],
    "auto_start": true,
    "max_sessions": 10
  }'

# 启动服务
curl -X POST http://localhost:8080/api/v1/services/{service_id}/start

# 获取服务统计
curl http://localhost:8080/api/v1/services/{service_id}/stats

# 获取系统统计
curl http://localhost:8080/api/v1/stats
```

#### Python httpx 示例

```python
import asyncio
import httpx

async def api_example():
    async with httpx.AsyncClient() as client:
        # 获取系统信息
        response = await client.get("http://localhost:8080/api/v1/info")
        print("System info:", response.json())
        
        # 创建服务
        service_data = {
            "name": "test-service",
            "agent_factory_path": "./my_agent.py",
            "description": "Test service",
            "tags": ["test"],
            "auto_start": True
        }
        response = await client.post(
            "http://localhost:8080/api/v1/services",
            json=service_data
        )
        service = response.json()
        service_id = service["service_id"]
        
        # 获取服务状态
        response = await client.get(f"http://localhost:8080/api/v1/services/{service_id}")
        print("Service status:", response.json()["status"])
        
        # 获取健康检查
        response = await client.get(f"http://localhost:8080/api/v1/services/{service_id}/health")
        print("Health check:", response.json()["status"])

if __name__ == "__main__":
    asyncio.run(api_example())
```

### 路由配置

```python
from myagent.manager.storage.models import (
    RoutingRule, RoutingCondition, RoutingStrategy, ConditionOperator
)

# 创建路由规则
rule = RoutingRule(
    name="vip-routing",
    priority=1,
    conditions=[
        RoutingCondition(
            field="user_agent",
            operator=ConditionOperator.CONTAINS,
            value="VIP",
            case_sensitive=False,
        )
    ],
    target_strategy=RoutingStrategy.LEAST_CONNECTIONS,
    target_tags=["premium"],
    description="Route VIP clients to premium services",
)

# 添加路由规则
manager.add_routing_rule(rule)
```

## 高级功能

### 健康监控

系统自动监控服务健康状态：

- **WebSocket 连通性检查**: 验证服务是否响应
- **进程状态检查**: 确认服务进程正在运行
- **自动故障恢复**: 不健康的服务会自动重启

### 路由策略

支持多种路由策略：

- **Round Robin**: 轮询分发
- **Least Connections**: 最少连接数优先
- **Weighted Random**: 加权随机
- **Hash-based**: 基于客户端 IP 的会话亲和性
- **Tag-based**: 基于服务标签的路由

### 自动重启

配置自动重启参数：

```python
config = ServiceConfig(
    auto_restart=True,        # 启用自动重启
    max_restart_count=3,      # 最大重启次数
    restart_delay=5,          # 重启延迟 (秒)
)
```

## 监控和调试

### 日志查看

系统使用结构化日志记录关键事件：

```bash
# 查看服务日志
tail -f myagent.log

# 过滤特定服务的日志
grep "weather-service" myagent.log
```

### 性能监控

通过统计 API 获取性能指标：

```python
# 获取连接统计
conn_stats = manager.get_connection_stats()
print(f"Active connections: {conn_stats['total_connections']}")

# 获取服务健康摘要
health_summary = manager.get_health_summary()
print(f"Healthy services: {health_summary['healthy']}")
```

### 数据持久化

系统使用 SQLite 数据库存储：

- 服务注册信息
- 路由规则配置
- 健康检查历史
- 统计数据

数据库文件位置: `agent_manager.db` (可自定义)

## 故障排除

### 常见问题

1. **端口冲突**
   ```
   Error: Port 8081 is not available
   ```
   解决方案: 使用 `--port` 指定其他端口，或让系统自动分配

2. **智能体文件未找到**
   ```
   Error: Agent factory file not found
   ```
   解决方案: 检查文件路径是否正确，使用绝对路径

3. **服务启动失败**
   ```
   Service status: error
   ```
   解决方案: 检查智能体文件是否有语法错误，查看详细错误信息

4. **连接路由失败**
   ```
   No available services for routing
   ```
   解决方案: 确保至少有一个服务处于运行状态

### 调试模式

启用详细日志记录：

```python
import logging
logging.getLogger("myagent.manager").setLevel(logging.DEBUG)
```

## 生产部署建议

### 系统要求

- Python 3.11+
- 足够的内存来运行多个智能体实例
- 稳定的网络连接
- 持久化存储 (用于数据库文件)

### 安全考虑

- 使用防火墙限制端口访问
- 配置 HTTPS/WSS (如需要)
- 定期备份数据库文件
- 监控系统资源使用

### 扩展性

- 根据负载调整服务实例数量
- 使用负载均衡器分发流量
- 考虑使用 Redis 进行分布式缓存
- 监控服务性能指标

## 示例场景

### 场景 1: 多语言客服系统

```bash
# 注册中文客服
python -m myagent.manager.cli.manager register chinese-support chinese_agent.py \\
    --tags "support,chinese" --auto-start

# 注册英文客服  
python -m myagent.manager.cli.manager register english-support english_agent.py \\
    --tags "support,english" --auto-start

# 创建语言路由规则 (通过编程接口)
```

### 场景 2: 负载均衡的 AI 服务

```bash
# 注册多个相同服务实例
for i in {1..3}; do
    python -m myagent.manager.cli.manager register ai-service-$i ai_agent.py \\
        --tags "ai,production" --auto-start
done

# 启动代理服务器进行负载均衡
python -m myagent.manager.cli.proxy --port 9090
```

## 总结

MyAgent WebSocket 管理系统提供了完整的多智能体部署和管理解决方案。通过简单的命令行工具和编程接口，您可以轻松地：

- 管理多个智能体服务的生命周期
- 实现智能连接路由和负载均衡
- 监控服务健康状态和性能
- 构建可扩展的 AI 服务架构

该系统适用于从开发测试到生产部署的各种场景，为构建复杂的智能体应用提供了坚实的基础设施支持。