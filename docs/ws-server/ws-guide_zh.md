# MyAgent WebSocket 模块完整指南

## 目录

1. [模块概述](#模块概述)
2. [核心组件](#核心组件)
3. [服务器端开发](#服务器端开发)
4. [客户端开发](#客户端开发)
5. [高级功能](#高级功能)
6. [最佳实践](#最佳实践)
7. [故障排除](#故障排除)

---

## 模块概述

MyAgent WebSocket 模块 (`myagent.ws`) 提供完整的 WebSocket 服务器实现，支持实时 Agent 交互、用户确认机制和客户端状态管理。

### 模块结构

```
myagent/ws/
├── __init__.py          # 模块导出
├── server.py            # AgentWebSocketServer - WebSocket服务器
├── session.py           # AgentSession - 会话管理
├── events.py            # 事件协议定义
├── state_manager.py     # StateManager - 状态管理
└── utils.py             # 工具函数（跨版本兼容）
```

### 主要特性

- ✅ 实时双向通信
- ✅ 会话管理和隔离
- ✅ 工具调用可视化
- ✅ 用户确认机制
- ✅ 客户端状态管理
- ✅ 心跳检测和自动重连
- ✅ 多会话并发支持

---

## 核心组件

### 1. AgentWebSocketServer

**位置:** `myagent.ws.server.AgentWebSocketServer`

**功能:** WebSocket 服务器主类，处理连接管理、会话创建和消息路由。

**初始化参数:**

```python
class AgentWebSocketServer:
    def __init__(
        self,
        agent_factory_func: Callable[[], BaseAgent],  # Agent工厂函数
        host: str = "localhost",                       # 服务器地址
        port: int = 8080,                              # 服务器端口
        state_secret_key: str = None,                  # 状态签名密钥（生产环境必需）
    )
```

**主要方法:**

- `async start_server()` - 启动 WebSocket 服务器
- `async shutdown()` - 优雅关闭服务器
- `get_status()` - 获取服务器状态信息

**使用示例:**

```python
from myagent.ws.server import AgentWebSocketServer

def create_agent():
    return create_toolcall_agent(tools=[...])

server = AgentWebSocketServer(
    agent_factory_func=create_agent,
    host="0.0.0.0",
    port=8080,
    state_secret_key="production-secret-key-here"
)

await server.start_server()
```

### 2. AgentSession

**位置:** `myagent.ws.session.AgentSession`

**功能:** 管理单个 Agent 会话的生命周期，处理 Agent 执行和事件流。

**关键属性:**

```python
class AgentSession:
    session_id: str              # 会话ID
    connection_id: str           # 连接ID
    agent: BaseAgent            # Agent实例
    websocket: WebSocketServerProtocol  # WebSocket连接
    state: str                  # 会话状态 (idle/running/closed)
    step_counter: int           # 步骤计数器
```

**主要方法:**

- `async execute_streaming(user_input)` - 流式执行 Agent
- `async handle_user_response(step_id, response_data)` - 处理用户响应
- `async cancel()` - 取消当前执行
- `async close()` - 关闭会话
- `is_active()` - 检查会话是否活跃

**内部机制:**

- 自动包装工具调用以发送实时事件
- 设置确认处理器用于需要用户确认的工具
- Agent 状态重置和内存清理
- WebSocket 会话上下文管理

### 3. StateManager

**位置:** `myagent.ws.state_manager.StateManager`

**功能:** 客户端状态管理，支持会话状态的序列化、签名和恢复。

**初始化:**

```python
from myagent.ws.state_manager import StateManager

state_manager = StateManager(
    secret_key="your-production-secret-key"
)
```

**核心方法:**

#### 创建状态快照

```python
state_data = state_manager.create_state_snapshot(session)
# 返回: Dict[str, Any] - 包含会话状态的字典
```

**状态数据结构:**

```python
{
    "session_id": "sess_xxx",
    "current_step": 5,
    "agent_state": "idle",
    "created_at": "2024-01-01T10:00:00Z",
    "last_active_at": "2024-01-01T10:30:00Z",
    "memory_snapshot": "[{...}, ...]",  # JSON字符串
    "tool_states": {...},
    "pending_confirmations": ["step_1", ...],
    "metadata": {...}
}
```

#### 签名状态

```python
signed_state = state_manager.sign_state(state_data)
# 返回: Dict[str, Any] - 包含签名的状态
```

**签名状态结构:**

```python
{
    "state": {...},              # 原始状态数据
    "timestamp": 1704110400,     # Unix时间戳
    "signature": "abc123...",    # HMAC-SHA256签名
    "version": "1.0",            # 状态格式版本
    "checksum": "def456..."      # SHA-256校验和
}
```

#### 验证状态

```python
is_valid, state_data, error_msg = state_manager.verify_state(signed_state)
# 返回: Tuple[bool, Dict, str]
```

**验证检查项:**

- ✅ 签名验证（HMAC-SHA256）
- ✅ 时间戳验证（防止重放攻击，7天有效期）
- ✅ 校验和验证（数据完整性）
- ✅ 版本兼容性检查
- ✅ 状态结构验证

#### 恢复会话

```python
success = state_manager.restore_session_from_state(session, state_data)
# 返回: bool - 恢复是否成功
```

**安全特性:**

1. **HMAC签名**: 使用服务器密钥签名，防止客户端篡改
2. **时间戳验证**: 状态有7天有效期，过期自动失效
3. **敏感信息清理**: 自动移除 API 密钥、令牌等
4. **大小限制**:
   - 最大状态大小: 100KB
   - 最大消息数: 100条
5. **校验和**: SHA-256 确保数据完整性

### 4. 事件协议

**位置:** `myagent.ws.events`

**事件类别:**

```python
# 用户事件（客户端 → 服务器）
class UserEvents:
    CREATE_SESSION = "user.create_session"
    MESSAGE = "user.message"
    RESPONSE = "user.response"
    CANCEL = "user.cancel"
    REQUEST_STATE = "user.request_state"
    RECONNECT_WITH_STATE = "user.reconnect_with_state"

# Agent事件（服务器 → 客户端）
class AgentEvents:
    SESSION_CREATED = "agent.session_created"
    THINKING = "agent.thinking"
    TOOL_CALL = "agent.tool_call"
    TOOL_RESULT = "agent.tool_result"
    USER_CONFIRM = "agent.user_confirm"
    PARTIAL_ANSWER = "agent.partial_answer"
    FINAL_ANSWER = "agent.final_answer"
    LLM_MESSAGE = "agent.llm_message"
    STATE_EXPORTED = "agent.state_exported"
    STATE_RESTORED = "agent.state_restored"
    ERROR = "agent.error"
    INTERRUPTED = "agent.interrupted"
    SESSION_END = "agent.session_end"

# 系统事件（服务器 → 客户端）
class SystemEvents:
    CONNECTED = "system.connected"
    HEARTBEAT = "system.heartbeat"
    ERROR = "system.error"
```

**事件消息格式:**

```python
class EventProtocol(BaseModel):
    session_id: str | None      # 会话ID (非系统事件必需)
    connection_id: str | None   # 连接ID
    step_id: str | None         # 步骤ID (用于确认关联)
    event: str                  # 事件类型
    timestamp: str              # ISO格式时间戳
    content: str | dict | None  # 事件内容
    metadata: dict | None       # 元数据
```

**创建事件:**

```python
from myagent.ws.events import create_event, AgentEvents

event = create_event(
    event_type=AgentEvents.THINKING,
    session_id="sess_123",
    content="正在思考...",
    metadata={"step": 1}
)
```

### 5. WebSocket 工具函数

**位置:** `myagent.ws.utils`

**跨版本兼容工具:**

```python
from myagent.ws.utils import (
    is_websocket_closed,
    send_websocket_message,
    close_websocket_safely,
    get_websocket_info
)

# 检查连接状态（兼容旧版和新版 websockets 库）
if not is_websocket_closed(websocket):
    # 安全发送消息
    success = await send_websocket_message(websocket, message_dict)

# 安全关闭连接
await close_websocket_safely(websocket)

# 获取调试信息
info = get_websocket_info(websocket)
```

**版本兼容性说明:**

- 旧版 `websockets`: 使用 `websocket.closed` 属性
- 新版 `websockets`: 使用 `websocket.close_code` 属性
- 工具函数自动检测版本并使用正确的方法

---

## 服务器端开发

### 基础服务器示例

```python
# server.py
import asyncio
from myagent import create_toolcall_agent
from myagent.ws.server import AgentWebSocketServer
from myagent.tool import BaseTool, ToolResult

# 1. 定义工具
class WeatherTool(BaseTool):
    name = "get_weather"
    description = "获取天气信息"

    async def execute(self, city: str) -> ToolResult:
        # 模拟天气查询
        return ToolResult(output=f"{city}的天气：晴天，25°C")

# 2. 定义Agent工厂函数
def create_agent():
    """每个会话创建一个新的Agent实例"""
    tools = [WeatherTool()]
    return create_toolcall_agent(
        tools=tools,
        name="weather_agent",
        description="天气查询助手"
    )

# 3. 创建并启动服务器
async def main():
    server = AgentWebSocketServer(
        agent_factory_func=create_agent,
        host="0.0.0.0",
        port=8080,
        state_secret_key="my-production-secret-key-2024"
    )

    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        await server.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### 启动服务器

```bash
# 直接运行
uv run python server.py

# 或使用CLI
uv run python -m myagent.cli.server server server.py --port 8080
```

### 需要用户确认的工具

```python
class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "删除文件（需要确认）"
    user_confirm = True  # 启用用户确认

    async def execute(self, file_path: str) -> ToolResult:
        # 工具执行前会自动请求用户确认
        # 用户确认后才会执行此代码
        return ToolResult(output=f"已删除文件: {file_path}")
```

### 服务器状态监控

```python
# 获取服务器状态
status = server.get_status()
print(status)
# {
#     "running": True,
#     "host": "0.0.0.0",
#     "port": 8080,
#     "total_connections": 5,
#     "total_sessions": 8,
#     "active_sessions": 3,
#     "server_time": "2024-01-01T12:00:00"
# }
```

---

## 客户端开发

### JavaScript/TypeScript 客户端

#### 基础连接

```javascript
class MyAgentClient {
    constructor(url = 'ws://localhost:8080') {
        this.url = url;
        this.ws = null;
        this.sessionId = null;
        this.messageHandlers = new Map();
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('✅ 已连接');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('❌ 连接关闭');
        };

        this.ws.onerror = (error) => {
            console.error('连接错误:', error);
        };
    }

    handleMessage(data) {
        const { event } = data;

        switch (event) {
            case 'system.connected':
                this.createSession();
                break;

            case 'agent.session_created':
                this.sessionId = data.session_id;
                console.log('会话创建:', this.sessionId);
                break;

            case 'agent.thinking':
                console.log('Agent正在思考...');
                break;

            case 'agent.tool_call':
                console.log('调用工具:', data.metadata.tool);
                break;

            case 'agent.tool_result':
                console.log('工具结果:', data.content);
                break;

            case 'agent.final_answer':
                console.log('最终答案:', data.content);
                break;

            case 'agent.user_confirm':
                this.handleConfirmation(data);
                break;

            case 'agent.error':
            case 'system.error':
                console.error('错误:', data.content);
                break;
        }
    }

    createSession() {
        this.send({
            event: 'user.create_session',
            timestamp: new Date().toISOString(),
            content: 'create_session'
        });
    }

    sendMessage(content) {
        if (!this.sessionId) {
            console.error('会话未创建');
            return;
        }

        this.send({
            session_id: this.sessionId,
            event: 'user.message',
            timestamp: new Date().toISOString(),
            content: content
        });
    }

    send(message) {
        this.ws.send(JSON.stringify(message));
    }
}

// 使用
const client = new MyAgentClient();
client.connect();

// 发送消息
setTimeout(() => {
    client.sendMessage('今天天气怎么样？');
}, 1000);
```

#### 用户确认处理

```javascript
class MyAgentClient {
    // ... 之前的代码 ...

    handleConfirmation(data) {
        const { step_id, metadata } = data;
        const { tool_name, tool_description, tool_args } = metadata;

        // 显示确认对话框
        const confirmed = confirm(
            `确认执行工具: ${tool_name}\n` +
            `描述: ${tool_description}\n` +
            `参数: ${JSON.stringify(tool_args, null, 2)}`
        );

        // 发送用户响应
        this.send({
            session_id: this.sessionId,
            event: 'user.response',
            step_id: step_id,
            timestamp: new Date().toISOString(),
            content: {
                confirmed: confirmed,
                message: confirmed ? '用户确认' : '用户取消'
            }
        });
    }
}
```

#### 状态管理

```javascript
class ClientStateManager {
    constructor(client) {
        this.client = client;
    }

    // 请求导出状态
    async requestStateExport() {
        return new Promise((resolve) => {
            const handler = (data) => {
                if (data.event === 'agent.state_exported') {
                    const signedState = data.metadata.signed_state;
                    resolve(signedState);
                }
            };

            this.client.messageHandlers.set('state_export', handler);

            this.client.send({
                event: 'user.request_state',
                session_id: this.client.sessionId,
                timestamp: new Date().toISOString()
            });
        });
    }

    // 保存状态到本地存储
    saveState(sessionId, signedState) {
        localStorage.setItem(
            `myagent_session_${sessionId}`,
            JSON.stringify(signedState)
        );
    }

    // 从本地存储加载状态
    loadState(sessionId) {
        const data = localStorage.getItem(`myagent_session_${sessionId}`);
        return data ? JSON.parse(data) : null;
    }

    // 使用状态重连
    reconnectWithState(signedState) {
        this.client.send({
            event: 'user.reconnect_with_state',
            signed_state: signedState,
            timestamp: new Date().toISOString()
        });
    }
}

// 使用示例
const stateManager = new ClientStateManager(client);

// 导出并保存状态
const signedState = await stateManager.requestStateExport();
stateManager.saveState(client.sessionId, signedState);

// 重新连接后恢复状态
const savedState = stateManager.loadState('original-session-id');
if (savedState) {
    stateManager.reconnectWithState(savedState);
}
```

### Python 客户端

```python
import asyncio
import json
import websockets
from datetime import datetime

class MyAgentClient:
    def __init__(self, url="ws://localhost:8080"):
        self.url = url
        self.websocket = None
        self.session_id = None

    async def connect(self):
        self.websocket = await websockets.connect(self.url)
        print("✅ 已连接")
        asyncio.create_task(self.listen())

    async def listen(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("❌ 连接关闭")

    async def handle_message(self, data):
        event = data.get('event')

        if event == 'system.connected':
            await self.create_session()
        elif event == 'agent.session_created':
            self.session_id = data.get('session_id')
            print(f"会话创建: {self.session_id}")
        elif event == 'agent.thinking':
            print("Agent正在思考...")
        elif event == 'agent.final_answer':
            print(f"最终答案: {data.get('content')}")
        elif event == 'agent.user_confirm':
            await self.handle_confirmation(data)

    async def create_session(self):
        await self.send({
            "event": "user.create_session",
            "timestamp": datetime.now().isoformat(),
            "content": "create_session"
        })

    async def send_message(self, content):
        await self.send({
            "session_id": self.session_id,
            "event": "user.message",
            "timestamp": datetime.now().isoformat(),
            "content": content
        })

    async def send(self, message):
        await self.websocket.send(json.dumps(message))

    async def handle_confirmation(self, data):
        step_id = data.get('step_id')
        metadata = data.get('metadata', {})

        print(f"\n⚠️ 确认请求:")
        print(f"工具: {metadata.get('tool_name')}")
        print(f"参数: {metadata.get('tool_args')}")

        # 简单示例：自动确认
        confirmed = True

        await self.send({
            "session_id": self.session_id,
            "event": "user.response",
            "step_id": step_id,
            "timestamp": datetime.now().isoformat(),
            "content": {
                "confirmed": confirmed,
                "message": "自动确认"
            }
        })

# 使用
async def main():
    client = MyAgentClient()
    await client.connect()
    await asyncio.sleep(1)
    await client.send_message("今天天气怎么样？")
    await asyncio.sleep(10)

asyncio.run(main())
```

---

## 高级功能

### 1. 多会话管理

服务器自动支持多个并发会话：

```python
# 服务器端 - 无需额外配置
# AgentWebSocketServer 自动管理多个会话

# 客户端 - 创建多个会话
sessions = []
for i in range(5):
    client = MyAgentClient()
    await client.connect()
    sessions.append(client)

# 每个会话独立运行
for session in sessions:
    await session.send_message(f"会话 {session.session_id} 的消息")
```

### 2. 心跳检测

服务器每60秒发送心跳：

```javascript
// 客户端处理心跳
handleMessage(data) {
    if (data.event === 'system.heartbeat') {
        console.log('心跳:', data.metadata);
        // metadata包含: { active_sessions, uptime }
    }
}
```

### 3. 会话取消

```javascript
// 取消正在运行的会话
cancelSession() {
    this.send({
        session_id: this.sessionId,
        event: 'user.cancel',
        timestamp: new Date().toISOString()
    });
}
```

### 4. LLM 消息事件（可选）

启用 LLM 消息事件以查看完整的对话历史：

```bash
# 设置环境变量
export SEND_LLM_MESSAGE=true

# 或在代码中
import os
os.environ['SEND_LLM_MESSAGE'] = 'true'
```

客户端处理：

```javascript
handleMessage(data) {
    if (data.event === 'agent.llm_message') {
        const { role, content } = data.metadata.message;
        console.log(`${role}: ${content}`);
    }
}
```

---

## 最佳实践

### 1. 安全性

```python
# ✅ 生产环境必须提供固定密钥
server = AgentWebSocketServer(
    agent_factory_func=create_agent,
    state_secret_key=os.environ.get('STATE_SECRET_KEY')  # 从环境变量读取
)

# ❌ 不要在代码中硬编码密钥
server = AgentWebSocketServer(
    agent_factory_func=create_agent,
    state_secret_key="hardcoded-secret"  # 不安全！
)

# ✅ 使用 WSS (WebSocket Secure)
# 在生产环境使用 Nginx/Caddy 反向代理提供 WSS
```

### 2. 错误处理

```python
# 服务器端
async def create_agent():
    try:
        agent = create_toolcall_agent(...)
        return agent
    except Exception as e:
        logger.error(f"Agent创建失败: {e}")
        raise

# 客户端
class MyAgentClient:
    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.url)
        except Exception as e:
            print(f"连接失败: {e}")
            # 实现重连逻辑
            await asyncio.sleep(5)
            await self.connect()
```

### 3. 资源管理

```python
# 优雅关闭
async def main():
    server = AgentWebSocketServer(...)

    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭...")
    finally:
        await server.shutdown()  # 清理所有会话和连接
```

### 4. 日志记录

```python
from myagent.logger import logger

# 服务器端自动记录关键事件
# 查看日志了解系统状态

# 客户端也应该记录事件
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MyAgentClient:
    async def handle_message(self, data):
        logger.info(f"收到事件: {data.get('event')}")
```

### 5. 状态管理

```javascript
// 定期导出状态（例如每次重要操作后）
class AutoStateManager {
    constructor(client) {
        this.client = client;
        this.autoSaveInterval = 60000; // 60秒
        this.startAutoSave();
    }

    startAutoSave() {
        setInterval(async () => {
            if (this.client.sessionId) {
                const state = await this.requestStateExport();
                this.saveState(this.client.sessionId, state);
            }
        }, this.autoSaveInterval);
    }
}
```

---

## 故障排除

### 常见问题

#### 1. 连接失败

**问题:** `WebSocket connection failed`

**解决方案:**
- 检查服务器是否运行
- 确认端口是否正确
- 检查防火墙设置
- 确认 URL 格式 (`ws://` 或 `wss://`)

```bash
# 检查端口是否监听
lsof -i :8080

# 测试连接
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8080
```

#### 2. 消息不响应

**问题:** 发送消息后没有响应

**解决方案:**
- 检查 `session_id` 是否正确
- 确认消息格式符合协议
- 查看服务器日志

```javascript
// 调试：打印发送的消息
send(message) {
    console.log('发送:', message);
    this.ws.send(JSON.stringify(message));
}
```

#### 3. 状态验证失败

**问题:** `Invalid state signature`

**解决方案:**
- 检查服务器密钥是否一致
- 确认状态数据未被修改
- 检查状态是否过期（7天）

```python
# 检查密钥配置
print(f"服务器密钥: {server.state_manager.secret_key[:10]}...")
```

#### 4. 确认请求超时

**问题:** 用户确认请求超时（5分钟）

**解决方案:**
- 确保 `step_id` 正确匹配
- 检查确认处理逻辑
- 增加超时时间（如果需要）

```python
# 在 AgentSession._wait_for_user_response 中调整超时
async def _wait_for_user_response(self, step_id: str, timeout: int = 600):  # 10分钟
    ...
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

2. **使用 WebSocket 调试工具**

- Chrome DevTools Network 标签
- [WebSocket King](https://websocketking.com/)
- [wscat](https://github.com/websockets/wscat)

```bash
# 使用 wscat 测试
npm install -g wscat
wscat -c ws://localhost:8080
```

3. **检查服务器状态**

```python
# 定期打印服务器状态
import asyncio

async def monitor_server(server):
    while True:
        status = server.get_status()
        print(f"状态: {status}")
        await asyncio.sleep(30)

# 在主函数中启动
asyncio.create_task(monitor_server(server))
```

### 性能优化

1. **消息批处理**

```javascript
// 避免频繁发送小消息
class MessageBatcher {
    constructor(client, interval = 100) {
        this.client = client;
        this.queue = [];
        this.interval = interval;
        this.timer = null;
    }

    add(message) {
        this.queue.push(message);
        if (!this.timer) {
            this.timer = setTimeout(() => this.flush(), this.interval);
        }
    }

    flush() {
        if (this.queue.length > 0) {
            // 批量处理消息
            this.queue.forEach(msg => this.client.send(msg));
            this.queue = [];
        }
        this.timer = null;
    }
}
```

2. **连接池**

```python
# 限制并发会话数
class SessionPool:
    def __init__(self, max_sessions=100):
        self.max_sessions = max_sessions
        self.semaphore = asyncio.Semaphore(max_sessions)

    async def acquire(self):
        await self.semaphore.acquire()

    def release(self):
        self.semaphore.release()
```

---

## 总结

MyAgent WebSocket 模块提供了完整的实时 Agent 交互解决方案，具有以下优势：

- ✅ **简单易用**: 清晰的 API 和丰富的示例
- ✅ **功能完整**: 支持确认机制、状态管理、多会话等
- ✅ **安全可靠**: HMAC 签名、状态验证、敏感信息清理
- ✅ **高性能**: 异步架构、心跳检测、自动清理
- ✅ **可扩展**: 支持自定义工具、事件处理和状态管理

通过本指南，你应该能够：

1. 理解 WebSocket 模块的核心组件
2. 创建自己的 WebSocket 服务器
3. 开发客户端应用
4. 实现高级功能
5. 解决常见问题

## 相关文档

- [快速开始](./quick-start.md) - 5分钟上手
- [基础概念](./basic-concepts.md) - 详细概念说明
- [用户确认机制](./user-confirmation.md) - 确认流程实现
- [客户端状态管理](./client-state-management.md) - 状态管理详解
- [React集成](./react-integration.md) - React 框架集成

## 获取帮助

如有问题，请：

1. 查看[基础概念文档](./basic-concepts.md)
2. 检查[故障排除](#故障排除)章节
3. 在 GitHub Issues 提出问题
