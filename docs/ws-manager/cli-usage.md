# MyAgent Manager CLI 使用指南

## 安装和配置

### 1. 安装依赖

确保所有依赖已安装：

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 2. 验证安装

```bash
# 查看 CLI 帮助
myagent-manager --help

# 或使用模块路径
python -m myagent.manager.cli --help
```

## 可用命令

### 服务管理命令

#### register - 注册服务
```bash
myagent-manager register <name> <agent_path> [OPTIONS]

选项:
  --host TEXT                  服务主机 (默认: localhost)
  --port INTEGER               服务端口 (自动分配 8081-9000)
  --description TEXT           服务描述
  --tags TEXT                  逗号分隔的标签
  --auto-start                 注册后自动启动
  --max-sessions INTEGER       最大会话数 (默认: 0 = 无限制)
  --session-timeout INTEGER    会话超时秒数 (默认: 1800)
  --auto-restart               启用自动重启 (默认: True)
  --health-check-interval INTEGER  健康检查间隔秒数 (默认: 10)

示例:
  myagent-manager register weather_service examples/weather_agent.py \
    --port 8081 \
    --tags production,weather \
    --auto-start
```

#### start - 启动服务
```bash
myagent-manager start <service_name>

示例:
  myagent-manager start weather_service
```

#### stop - 停止服务
```bash
myagent-manager stop <service_name>

示例:
  myagent-manager stop weather_service
```

#### restart - 重启服务
```bash
myagent-manager restart <service_name>

示例:
  myagent-manager restart weather_service
```

#### unregister - 注销服务
```bash
myagent-manager unregister <service_name>

示例:
  myagent-manager unregister weather_service
```

#### list - 列出服务
```bash
myagent-manager list [OPTIONS]

选项:
  --status [stopped|starting|running|stopping|error|unhealthy]
  --tags TEXT                  逗号分隔的标签
  --format [table|json]        输出格式 (默认: table)

示例:
  # 列出所有服务
  myagent-manager list

  # 只显示运行中的服务
  myagent-manager list --status running

  # 筛选特定标签
  myagent-manager list --tags production

  # JSON 格式输出
  myagent-manager list --format json
```

#### status - 查看服务状态
```bash
myagent-manager status <service_name> [OPTIONS]

选项:
  --format [table|json]        输出格式 (默认: table)

示例:
  myagent-manager status weather_service
  myagent-manager status weather_service --format json
```

#### stats - 系统统计
```bash
myagent-manager stats

示例:
  myagent-manager stats
```

### 服务器命令

#### daemon - 守护进程模式
```bash
myagent-manager daemon [OPTIONS]

选项:
  --interval INTEGER           健康检查间隔秒数 (默认: 10)

示例:
  myagent-manager daemon
  myagent-manager daemon --interval 5
```

#### api - HTTP API 服务器
```bash
myagent-manager api [OPTIONS]

选项:
  --host TEXT                  API 服务器主机 (默认: 0.0.0.0)
  --port INTEGER               API 服务器端口 (默认: 8080)
  --db-path TEXT               数据库路径 (默认: agent_manager.db)
  --health-interval INTEGER    健康检查间隔 (默认: 10)
  --proxy-port INTEGER         同时启动代理服务器在此端口

示例:
  # 基础启动
  myagent-manager api

  # 自定义端口
  myagent-manager api --port 8000

  # 同时启动代理服务器
  myagent-manager api --port 8000 --proxy-port 9000
```

启动后访问:
- API 文档: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

#### proxy - WebSocket 代理服务器
```bash
myagent-manager proxy [OPTIONS]

选项:
  --host TEXT                  代理服务器主机 (默认: localhost)
  --port INTEGER               代理服务器端口 (默认: 9090)
  --db-path TEXT               数据库路径 (默认: agent_manager.db)
  --health-interval INTEGER    健康检查间隔 (默认: 10)

示例:
  myagent-manager proxy
  myagent-manager proxy --port 9000
```

## 全局选项

所有服务管理命令都支持 `--db-path` 选项：

```bash
myagent-manager --db-path /path/to/custom.db <command>
```

## 完整工作流示例

### 示例 1: 快速启动单个服务

```bash
# 1. 注册并启动服务
myagent-manager register my_agent examples/weather_agent.py --auto-start

# 2. 查看服务状态
myagent-manager status my_agent

# 3. 测试服务 (使用 wscat 或其他 WebSocket 客户端)
# ws://localhost:8081
```

### 示例 2: 管理多个服务

```bash
# 1. 注册多个服务
myagent-manager register chat_agent examples/chat_agent.py \
  --port 8081 --tags production,chat --auto-start

myagent-manager register weather_agent examples/weather_agent.py \
  --port 8082 --tags production,weather --auto-start

myagent-manager register test_agent examples/test_agent.py \
  --port 8083 --tags development,test

# 2. 列出所有服务
myagent-manager list

# 3. 只启动测试服务
myagent-manager start test_agent

# 4. 查看生产环境服务
myagent-manager list --tags production
```

### 示例 3: 启动完整管理平台

```bash
# 1. 在一个终端启动 API 服务器和代理
myagent-manager api --port 8000 --proxy-port 9000

# 2. 在另一个终端注册服务
myagent-manager register my_agent examples/agent.py --auto-start

# 3. 通过 API 访问
curl http://localhost:8000/api/v1/services

# 4. 通过代理连接
# WebSocket 客户端连接到 ws://localhost:9000
```

### 示例 4: 守护进程模式

```bash
# 启动守护进程（自动健康检查和重启）
myagent-manager daemon --interval 10

# 守护进程会：
# - 每 10 秒检查所有服务健康状态
# - 自动重启失败的服务
# - 持续运行直到 Ctrl+C
```

## 进阶用法

### 使用 Python 模块路径

如果不想使用安装的命令，可以直接使用模块路径：

```bash
# 等价于 myagent-manager
python -m myagent.manager.cli <command>

# 使用 uv
uv run python -m myagent.manager.cli <command>
```

### 自定义数据库位置

```bash
# 所有命令都支持自定义数据库路径
myagent-manager --db-path /var/lib/myagent/manager.db list
myagent-manager --db-path /var/lib/myagent/manager.db register ...
```

### 输出 JSON 格式

便于脚本处理：

```bash
# 获取 JSON 格式的服务列表
myagent-manager list --format json | jq '.[] | .name'

# 获取服务详情
myagent-manager status my_agent --format json | jq '.status'
```

## 常见问题

### Q: 如何查看所有可用命令？

```bash
myagent-manager --help
```

### Q: 服务启动失败怎么办？

```bash
# 1. 查看服务状态和错误信息
myagent-manager status <service_name>

# 2. 检查端口是否被占用
lsof -i :<port>

# 3. 尝试重启服务
myagent-manager restart <service_name>
```

### Q: 如何停止所有服务？

目前需要逐个停止，或使用 API：

```bash
# 方法 1: 列出并逐个停止
myagent-manager list --status running | grep ... | xargs -n1 myagent-manager stop

# 方法 2: 使用 Python API
python -c "
import asyncio
from myagent.manager import AgentManager

async def stop_all():
    async with AgentManager() as mgr:
        await mgr.stop_all_services()

asyncio.run(stop_all())
"
```

### Q: 如何修改服务配置？

目前需要先注销再重新注册：

```bash
myagent-manager unregister my_service
myagent-manager register my_service /path/to/agent.py --port 8082 --auto-start
```

## 相关文档

- [完整管理指南](./manager-guide_zh.md) - 详细的管理系统文档
- [API 参考](./api-design.md) - HTTP API 详细文档
- [数据模型](./data-models.md) - 数据模型定义

## 获取帮助

```bash
# 查看全局帮助
myagent-manager --help

# 查看特定命令帮助
myagent-manager <command> --help

# 示例
myagent-manager register --help
myagent-manager api --help
```
