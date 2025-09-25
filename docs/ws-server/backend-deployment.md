# MyAgent WebSocket 一键部署方案

基于现有的 MyAgent 框架，提供一键部署 WebSocket Agent 服务的完整解决方案。

---

## 1. 架构概述

### 1.1 现有 MyAgent 架构分析

```
MyAgent 核心组件：
├── BaseAgent (基础代理类)
│   ├── 状态管理 (AgentState)
│   ├── 记忆管理 (Memory)
│   ├── 执行追踪 (Tracing)
│   └── 生命周期控制
├── ToolCallAgent (工具调用代理)
├── ReActAgent (推理-行动循环)
├── BaseTool (工具基类)
├── ToolCollection (工具集合)
└── LLM (大语言模型集成)
```

### 1.2 WebSocket 集成架构

```
WebSocket Agent 服务架构：
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │◄──►│  WebSocket       │◄──►│   MyAgent       │
│                 │    │  Gateway         │    │   Instance      │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│• 实时消息流     │    │• 连接管理        │    │• 推理循环       │
│• 用户交互       │    │• 事件路由        │    │• 工具调用       │
│• 状态显示       │    │• 会话管理        │    │• 状态管理       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 2. 核心设计

### 2.1 WebSocket 事件映射

将 MyAgent 的执行流程映射到 WebSocket 事件：

```python
# MyAgent 状态 → WebSocket 事件映射
AGENT_STATE_TO_EVENT = {
    AgentState.IDLE: "agent.ready",
    AgentState.RUNNING: "agent.thinking", 
    AgentState.FINISHED: "agent.final_answer",
    AgentState.ERROR: "agent.error"
}

# MyAgent 步骤 → WebSocket 事件映射
AGENT_STEP_TO_EVENT = {
    "thinking": "agent.thinking",
    "tool_call": "agent.tool_call", 
    "tool_result": "agent.tool_result",
    "response": "agent.partial_answer"
}
```

### 2.2 会话生命周期管理

```python
class AgentSession:
    """管理单个 Agent 会话的完整生命周期"""
    def __init__(self, session_id: str, agent_config: dict):
        self.session_id = session_id
        self.agent = self._create_agent(agent_config)
        self.websocket = None
        self.state = "idle"
        self.created_at = datetime.now()
        
    async def handle_message(self, message: dict) -> None:
        """处理来自客户端的消息"""
        if message["event"] == "user.message":
            await self._execute_agent(message["content"])
            
    async def _execute_agent(self, user_input: str) -> None:
        """执行 Agent 并实时推送状态"""
        async for event in self.agent.stream_run(user_input):
            await self._send_event(event)
```

---

## 3. 实现方案

### 3.1 WebSocket 服务器核心

```python
# myagent/ws/server.py
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Optional, Any
import websockets
from websockets.server import WebSocketServerProtocol

from ..agent.factory import create_react_agent
from ..schema import AgentState
from .session import AgentSession
from .events import EventProtocol


class AgentWebSocketServer:
    """MyAgent WebSocket 服务器"""
    
    def __init__(self, agent_factory_func, host="localhost", port=8080):
        self.agent_factory_func = agent_factory_func
        self.host = host
        self.port = port
        self.sessions: Dict[str, AgentSession] = {}
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """处理新的 WebSocket 连接"""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        
        try:
            # 发送连接确认
            await self._send_event(websocket, {
                "event": "system.connected",
                "connection_id": connection_id,
                "timestamp": datetime.now().isoformat()
            })
            
            async for message in websocket:
                await self._handle_message(websocket, connection_id, json.loads(message))
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # 清理连接和会话
            await self._cleanup_connection(connection_id)
    
    async def _handle_message(self, websocket: WebSocketServerProtocol, 
                            connection_id: str, message: dict):
        """处理接收到的消息"""
        event_type = message.get("event")
        session_id = message.get("session_id")
        
        if event_type == "user.create_session":
            # 创建新会话
            session_id = await self._create_session(websocket, connection_id, message)
            
        elif event_type == "user.message" and session_id:
            # 处理用户消息
            await self._handle_user_message(websocket, session_id, message)
            
        elif event_type == "user.cancel" and session_id:
            # 取消执行
            await self._cancel_session(session_id)
    
    async def _create_session(self, websocket: WebSocketServerProtocol, 
                            connection_id: str, message: dict) -> str:
        """创建新的 Agent 会话"""
        session_id = str(uuid.uuid4())
        
        # 使用工厂函数创建 Agent
        agent = self.agent_factory_func()
        
        # 创建会话
        session = AgentSession(
            session_id=session_id,
            connection_id=connection_id,
            agent=agent,
            websocket=websocket
        )
        
        self.sessions[session_id] = session
        
        # 发送会话创建确认
        await self._send_event(websocket, {
            "event": "agent.session_created",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return session_id
    
    async def _handle_user_message(self, websocket: WebSocketServerProtocol,
                                 session_id: str, message: dict):
        """处理用户消息，执行 Agent"""
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(websocket, {
                "event": "agent.error", 
                "error": "Session not found",
                "session_id": session_id
            })
            return
            
        # 执行 Agent 并流式推送结果
        user_input = message.get("content", "")
        await session.execute_streaming(user_input)
    
    async def _send_event(self, websocket: WebSocketServerProtocol, event: dict):
        """发送事件到客户端"""
        await websocket.send(json.dumps(event))
        
    async def start_server(self):
        """启动 WebSocket 服务器"""
        print(f"🚀 MyAgent WebSocket 服务启动在 ws://{self.host}:{self.port}")
        async with websockets.serve(self.handle_connection, self.host, self.port):
            await asyncio.Future()  # 永远运行
```

### 3.2 Agent 会话管理

```python
# myagent/ws/session.py
import asyncio
from datetime import datetime
from typing import Optional, AsyncGenerator, Dict, Any
from websockets.server import WebSocketServerProtocol

from ..agent.base import BaseAgent
from ..schema import AgentState, Message, Role
from ..trace import get_trace_manager


class AgentSession:
    """管理单个 Agent 实例的 WebSocket 会话"""
    
    def __init__(self, session_id: str, connection_id: str, 
                 agent: BaseAgent, websocket: WebSocketServerProtocol):
        self.session_id = session_id
        self.connection_id = connection_id
        self.agent = agent
        self.websocket = websocket
        self.state = "idle"
        self.created_at = datetime.now()
        self.current_task = None
        
    async def execute_streaming(self, user_input: str) -> None:
        """流式执行 Agent 并实时推送状态"""
        if self.state == "running":
            await self._send_event({
                "event": "agent.error",
                "session_id": self.session_id,
                "error": "Agent is already running"
            })
            return
            
        self.state = "running"
        
        try:
            # 发送开始执行事件
            await self._send_event({
                "event": "agent.thinking",
                "session_id": self.session_id,
                "content": "开始处理您的请求...",
                "timestamp": datetime.now().isoformat()
            })
            
            # 设置 Agent 回调来实时推送状态
            self.agent.set_step_callback(self._on_agent_step)
            
            # 执行 Agent
            result = await self.agent.arun(user_input)
            
            # 发送最终结果
            await self._send_event({
                "event": "agent.final_answer",
                "session_id": self.session_id,
                "content": result,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            await self._send_event({
                "event": "agent.error",
                "session_id": self.session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        finally:
            self.state = "idle"
    
    async def _on_agent_step(self, step_info: Dict[str, Any]) -> None:
        """Agent 步骤回调，实时推送执行状态"""
        step_type = step_info.get("type")
        
        if step_type == "thinking":
            await self._send_event({
                "event": "agent.thinking", 
                "session_id": self.session_id,
                "content": step_info.get("content", ""),
                "metadata": {"step": step_info.get("step", 0)}
            })
            
        elif step_type == "tool_call":
            await self._send_event({
                "event": "agent.tool_call",
                "session_id": self.session_id,
                "step_id": step_info.get("step_id"),
                "metadata": {
                    "tool": step_info.get("tool_name"),
                    "args": step_info.get("args", {}),
                    "status": "running"
                }
            })
            
        elif step_type == "tool_result":
            await self._send_event({
                "event": "agent.tool_result",
                "session_id": self.session_id, 
                "step_id": step_info.get("step_id"),
                "content": step_info.get("result"),
                "metadata": {
                    "tool": step_info.get("tool_name"),
                    "status": "success" if not step_info.get("error") else "failed"
                }
            })
    
    async def _send_event(self, event: dict) -> None:
        """发送事件到客户端"""
        try:
            await self.websocket.send(json.dumps(event))
        except Exception as e:
            print(f"Failed to send event: {e}")
    
    async def cancel(self) -> None:
        """取消当前执行"""
        if self.current_task:
            self.current_task.cancel()
        self.state = "idle"
        
        await self._send_event({
            "event": "agent.interrupted",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat()
        })
```

### 3.3 CLI 命令行工具

```python
# myagent/cli/server.py
import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Callable, Any

from ..ws.server import AgentWebSocketServer


def load_agent_from_file(file_path: str) -> Callable[[], Any]:
    """从 Python 文件动态加载 Agent"""
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        raise FileNotFoundError(f"Agent file not found: {file_path}")
    
    # 动态加载模块
    spec = importlib.util.spec_from_file_location("agent_module", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_module"] = module
    spec.loader.exec_module(module)
    
    # 查找 agent 变量
    if not hasattr(module, 'agent'):
        raise AttributeError(f"No 'agent' variable found in {file_path}")
    
    agent_instance = module.agent
    
    # 创建工厂函数
    def agent_factory():
        # 每次创建新的 agent 实例（深拷贝配置）
        return agent_instance.model_copy(deep=True)
    
    return agent_factory


def create_server_command():
    """创建 server 子命令"""
    parser = argparse.ArgumentParser(
        description="启动 MyAgent WebSocket 服务器"
    )
    
    parser.add_argument(
        "agent_file",
        help="Agent 配置文件路径 (Python 文件，包含 'agent' 变量)"
    )
    
    parser.add_argument(
        "--host",
        default="localhost", 
        help="服务器主机地址 (默认: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="服务器端口 (默认: 8080)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    return parser


async def run_server(args):
    """运行 WebSocket 服务器"""
    print(f"🔍 加载 Agent 文件: {args.agent_file}")
    
    try:
        agent_factory = load_agent_from_file(args.agent_file)
        print(f"✅ Agent 加载成功")
    except Exception as e:
        print(f"❌ Agent 加载失败: {e}")
        return 1
    
    # 创建并启动服务器
    server = AgentWebSocketServer(
        agent_factory_func=agent_factory,
        host=args.host,
        port=args.port
    )
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        return 0


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="myagent-ws",
        description="MyAgent WebSocket 部署工具"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # server 子命令
    server_parser = subparsers.add_parser("server", help="启动 WebSocket 服务器")
    server_parser.add_argument("agent_file", help="Agent 配置文件")
    server_parser.add_argument("--host", default="localhost", help="主机地址")
    server_parser.add_argument("--port", type=int, default=8080, help="端口")
    server_parser.add_argument("--debug", action="store_true", help="调试模式")
    
    args = parser.parse_args()
    
    if args.command == "server":
        return asyncio.run(run_server(args))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## 4. Agent 文件规范

### 4.1 标准 Agent 文件格式

```python
# sample_agent.py - 用户需要创建的 Agent 配置文件
from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult

# 定义自定义工具
class WeatherTool(BaseTool):
    name = "get_weather"
    description = "获取天气信息"
    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称"}
        },
        "required": ["city"]
    }
    
    async def execute(self, city: str) -> ToolResult:
        # 模拟天气查询
        return ToolResult(
            output=f"{city}的天气：晴朗，25°C",
            system="Weather query completed"
        )

# 创建 Agent 实例 (必须命名为 'agent')
agent = create_react_agent(
    name="weather-assistant",
    tools=[WeatherTool()],
    system_prompt="你是一个天气助手，可以查询天气信息。",
    next_step_prompt="如需查询天气，请使用 get_weather 工具。",
    max_steps=5
)
```

### 4.2 复杂 Agent 示例

```python
# complex_agent.py
import os
from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult

class DatabaseTool(BaseTool):
    name = "query_database"
    description = "查询数据库"
    
    async def execute(self, query: str) -> ToolResult:
        # 数据库查询逻辑
        return ToolResult(output="Query result")

class EmailTool(BaseTool):
    name = "send_email"
    description = "发送邮件"
    
    async def execute(self, to: str, subject: str, body: str) -> ToolResult:
        # 邮件发送逻辑
        return ToolResult(output=f"Email sent to {to}")

# 多工具 Agent
agent = create_react_agent(
    name="business-assistant",
    tools=[DatabaseTool(), EmailTool()],
    system_prompt="""你是一个业务助手，可以：
    1. 查询数据库获取信息
    2. 发送邮件通知
    请根据用户需求选择合适的工具。""",
    max_steps=10,
    enable_tracing=True  # 启用执行追踪
)
```

---

## 5. 使用方法

### 5.1 基本使用

```bash
# 1. 创建 Agent 文件
# 编写 my_agent.py，定义 agent 变量

# 2. 启动 WebSocket 服务
myagent-ws server my_agent.py --host 0.0.0.0 --port 8080

# 3. 服务启动成功
🔍 加载 Agent 文件: my_agent.py
✅ Agent 加载成功  
🚀 MyAgent WebSocket 服务启动在 ws://0.0.0.0:8080
```

### 5.2 高级选项

```bash
# 指定主机和端口
myagent-ws server agent.py --host 0.0.0.0 --port 9000

# 启用调试模式
myagent-ws server agent.py --debug

# 查看帮助
myagent-ws --help
myagent-ws server --help
```

---

## 6. 客户端连接示例

### 6.1 JavaScript 客户端

```javascript
const ws = new WebSocket('ws://localhost:8080');

// 连接成功
ws.onopen = () => {
    console.log('Connected to MyAgent WebSocket');
    
    // 创建会话
    ws.send(JSON.stringify({
        event: 'user.create_session',
        timestamp: new Date().toISOString()
    }));
};

// 接收消息
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
    
    switch(message.event) {
        case 'agent.session_created':
            // 会话创建成功，发送用户消息
            sessionId = message.session_id;
            sendUserMessage('查询北京天气');
            break;
            
        case 'agent.thinking':
            console.log('Agent thinking:', message.content);
            break;
            
        case 'agent.tool_call':
            console.log('Tool call:', message.metadata.tool);
            break;
            
        case 'agent.final_answer':
            console.log('Final answer:', message.content);
            break;
    }
};

function sendUserMessage(content) {
    ws.send(JSON.stringify({
        event: 'user.message',
        session_id: sessionId,
        content: content,
        timestamp: new Date().toISOString()
    }));
}
```

### 6.2 Python 客户端

```python
import asyncio
import json
import websockets

async def client_example():
    uri = "ws://localhost:8080"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to MyAgent WebSocket")
        
        # 创建会话
        await websocket.send(json.dumps({
            "event": "user.create_session",
            "timestamp": datetime.now().isoformat()
        }))
        
        session_id = None
        
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")
            
            if data["event"] == "agent.session_created":
                session_id = data["session_id"]
                # 发送用户消息
                await websocket.send(json.dumps({
                    "event": "user.message",
                    "session_id": session_id,
                    "content": "查询上海天气",
                    "timestamp": datetime.now().isoformat()
                }))
            elif data["event"] == "agent.final_answer":
                print(f"Final answer: {data['content']}")
                break

# 运行客户端
asyncio.run(client_example())
```

---

## 7. 部署和运维

### 7.1 Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制代码
COPY . .

# 安装 myagent
RUN pip install -e .

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["myagent-ws", "server", "agent.py", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
# 构建镜像
docker build -t myagent-ws .

# 运行容器
docker run -p 8080:8080 -v ./my_agent.py:/app/agent.py myagent-ws
```

### 7.2 生产部署建议

```yaml
# docker-compose.yml
version: '3.8'

services:
  myagent-ws:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./agents:/app/agents
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SERPER_API_KEY=${SERPER_API_KEY}
    command: ["myagent-ws", "server", "/app/agents/production_agent.py", "--host", "0.0.0.0"]
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - myagent-ws
```

---

## 8. 错误处理和监控

### 8.1 错误处理

```python
# 在 Agent 文件中添加错误处理
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobustTool(BaseTool):
    async def execute(self, **kwargs) -> ToolResult:
        try:
            # 工具逻辑
            result = await some_api_call(**kwargs)
            return ToolResult(output=result)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                error=f"工具执行失败: {str(e)}",
                system="Tool execution error"
            )
```

### 8.2 健康检查

```python
# 添加健康检查端点
from aiohttp import web

async def health_check(request):
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(server.sessions)
    })

# 在服务器中集成 HTTP 健康检查
app = web.Application()
app.router.add_get('/health', health_check)
web.run_app(app, host='localhost', port=8081)
```

---

## 9. 扩展和自定义

### 9.1 自定义事件处理

```python
# 在 Agent 文件中自定义事件处理
class CustomAgentSession(AgentSession):
    async def handle_custom_event(self, event_data):
        # 自定义事件处理逻辑
        pass

# 扩展服务器
class CustomWebSocketServer(AgentWebSocketServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加自定义配置
```

### 9.2 中间件支持

```python
# 添加认证中间件
class AuthMiddleware:
    async def process_message(self, websocket, message):
        # 验证用户权限
        if not self.validate_token(message.get("token")):
            await websocket.send(json.dumps({
                "event": "auth.error",
                "error": "Invalid token"
            }))
            return False
        return True
```

这个方案提供了从简单的单文件 Agent 到复杂的生产级部署的完整解决方案，用户只需要按照规范创建 Agent 文件，就可以一键部署为 WebSocket 服务。