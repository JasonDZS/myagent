# MyAgent WebSocket 快速开始

## 5分钟上手指南

本指南帮你快速建立 MyAgent WebSocket 连接并实现基本的对话功能。

## 1. 基本连接

### HTML + JavaScript 版本

```html
<!DOCTYPE html>
<html>
<head>
    <title>MyAgent WebSocket 测试</title>
</head>
<body>
    <div id="messages"></div>
    <input type="text" id="messageInput" placeholder="输入你的消息...">
    <button onclick="sendMessage()">发送</button>

    <script>
        let ws = null;
        let sessionId = null;

        // 连接WebSocket
        function connect() {
            ws = new WebSocket('ws://localhost:8080');
            
            ws.onopen = () => {
                console.log('✅ 已连接');
                addMessage('系统', '已连接到服务器');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onclose = () => {
                console.log('❌ 连接关闭');
                addMessage('系统', '连接已断开');
            };
        }

        // 处理接收到的消息
        function handleMessage(data) {
            const { event, session_id, content } = data;
            
            switch (event) {
                case 'system.connected':
                    // 自动创建会话
                    createSession();
                    break;
                    
                case 'agent.session_created':
                    sessionId = session_id;
                    addMessage('系统', '会话创建成功');
                    break;
                    
                case 'agent.thinking':
                    addMessage('Agent', '💭 正在思考...');
                    break;
                    
                case 'agent.final_answer':
                    addMessage('Agent', content);
                    break;
                    
                case 'agent.error':
                case 'system.error':
                    addMessage('错误', content);
                    break;
            }
        }

        // 创建会话
        function createSession() {
            const message = {
                event: 'user.create_session',
                timestamp: new Date().toISOString(),
                content: 'create_session'
            };
            ws.send(JSON.stringify(message));
        }

        // 发送消息
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const content = input.value.trim();
            
            if (!content || !sessionId) return;
            
            const message = {
                session_id: sessionId,
                event: 'user.message',
                timestamp: new Date().toISOString(),
                content: content
            };
            
            ws.send(JSON.stringify(message));
            addMessage('用户', content);
            input.value = '';
        }

        // 添加消息到页面
        function addMessage(sender, content) {
            const messages = document.getElementById('messages');
            const div = document.createElement('div');
            div.innerHTML = `<strong>${sender}:</strong> ${content}`;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        // 页面加载时自动连接
        window.onload = connect;
        
        // 回车发送消息
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
```

### 可选：直接任务模式（跳过规划）

```javascript
// 在收到 agent.session_created 后，直接提交任务给求解器：
ws.send(JSON.stringify({
  event: 'user.solve_tasks',
  session_id: sessionId,
  content: {
    tasks: [{ id: 1, title: '示例页', objective: '展示销售概览' }],
    // question: '可选，问题背景',
    // plan_summary: '可选，计划摘要'
  }
}));
// 将收到 solver.start / solver.completed 等求解相关事件
```

### 可选：客户端 ACK（推荐）

为提高可靠性与断线差量回放效果，建议按节流策略回传 ACK：

```javascript
let lastEventId = null; // 从下行消息的 event_id 更新
let lastSeq = 0;        // 从下行消息的 seq 更新

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (typeof msg.event_id === 'string') lastEventId = msg.event_id;
  if (typeof msg.seq === 'number') lastSeq = msg.seq;
  handleMessage(msg);
};

// 每 200ms 节流发送一次 ACK（也可每 N 条事件发送一次）
setInterval(() => {
  if (ws.readyState !== WebSocket.OPEN) return;
  const content = lastEventId ? { last_event_id: lastEventId } : { last_seq: lastSeq };
  ws.send(JSON.stringify({ event: 'user.ack', content }));
}, 200);
```

## 2. Node.js 版本

### 安装依赖

```bash
npm install ws
```

### 基础客户端

```javascript
// client.js
const WebSocket = require('ws');

class MyAgentClient {
    constructor(url = 'ws://localhost:8080') {
        this.url = url;
        this.ws = null;
        this.sessionId = null;
    }

    async connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.url);

            this.ws.on('open', () => {
                console.log('✅ 连接成功');
                resolve();
            });

            this.ws.on('message', (data) => {
                const message = JSON.parse(data.toString());
                this.handleMessage(message);
            });

            this.ws.on('close', () => {
                console.log('❌ 连接关闭');
            });

            this.ws.on('error', (error) => {
                console.error('连接错误:', error);
                reject(error);
            });
        });
    }

    handleMessage(data) {
        const { event, session_id, content } = data;

        switch (event) {
            case 'system.connected':
                this.createSession();
                break;

            case 'agent.session_created':
                this.sessionId = session_id;
                console.log('🚀 会话创建成功:', session_id);
                break;

            case 'agent.thinking':
                console.log('💭', content);
                break;

            case 'agent.final_answer':
                console.log('🎯 Agent回答:', content);
                break;

            case 'agent.error':
            case 'system.error':
                console.error('❌ 错误:', content);
                break;

            default:
                console.log('📨 其他消息:', data);
        }
    }

    createSession() {
        const message = {
            event: 'user.create_session',
            timestamp: new Date().toISOString(),
            content: 'create_session'
        };
        this.send(message);
    }

    sendMessage(content) {
        if (!this.sessionId) {
            console.error('会话未创建');
            return;
        }

        const message = {
            session_id: this.sessionId,
            event: 'user.message',
            timestamp: new Date().toISOString(),
            content: content
        };
        this.send(message);
    }

    send(message) {
        this.ws.send(JSON.stringify(message));
    }
}

// 使用示例
async function main() {
    const client = new MyAgentClient();
    
    try {
        await client.connect();
        
        // 等待会话创建
        setTimeout(() => {
            client.sendMessage('你好，请介绍一下自己');
        }, 1000);
        
    } catch (error) {
        console.error('连接失败:', error);
    }
}

main();
```

## 3. Python 版本

### 安装依赖

```bash
pip install websockets asyncio
```

### 基础客户端

```python
# client.py
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
        """连接到WebSocket服务器"""
        self.websocket = await websockets.connect(self.url)
        print("✅ 连接成功")
        
        # 启动消息处理循环
        asyncio.create_task(self.listen())

    async def listen(self):
        """监听服务器消息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("❌ 连接关闭")

    async def handle_message(self, data):
        """处理接收到的消息"""
        event = data.get('event')
        session_id = data.get('session_id')
        content = data.get('content')

        if event == 'system.connected':
            await self.create_session()
        elif event == 'agent.session_created':
            self.session_id = session_id
            print(f"🚀 会话创建成功: {session_id}")
        elif event == 'agent.thinking':
            print(f"💭 {content}")
        elif event == 'agent.final_answer':
            print(f"🎯 Agent回答: {content}")
        elif event in ['agent.error', 'system.error']:
            print(f"❌ 错误: {content}")
        else:
            print(f"📨 其他消息: {data}")

    async def create_session(self):
        """创建会话"""
        message = {
            "event": "user.create_session",
            "timestamp": datetime.now().isoformat(),
            "content": "create_session"
        }
        await self.send(message)

    async def send_message(self, content):
        """发送用户消息"""
        if not self.session_id:
            print("会话未创建")
            return

        message = {
            "session_id": self.session_id,
            "event": "user.message",
            "timestamp": datetime.now().isoformat(),
            "content": content
        }
        await self.send(message)

    async def send(self, message):
        """发送消息到服务器"""
        await self.websocket.send(json.dumps(message))

# 使用示例
async def main():
    client = MyAgentClient()
    
    await client.connect()
    
    # 等待会话创建
    await asyncio.sleep(1)
    
    # 发送测试消息
    await client.send_message("你好，请介绍一下自己")
    
    # 保持连接
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. 启动服务器

确保你的 MyAgent WebSocket 服务器正在运行：

```bash
# 使用示例 Agent
uv run python -m myagent.cli.server server examples/weather_agent.py --port 8080

# 或使用自定义 Agent
uv run python -m myagent.cli.server server your_agent.py --host localhost --port 8080

# 等价脚本（如已在 PATH 中）
scripts/myagent-ws server examples/weather_agent.py --port 8080
```

### 服务器端代码示例

创建自己的 WebSocket Agent 服务器：

```python
# my_agent_server.py
import asyncio
from myagent import create_toolcall_agent
from myagent.ws.server import AgentWebSocketServer
from myagent.tool import BaseTool, ToolResult

class MyTool(BaseTool):
    name = "my_tool"
    description = "示例工具"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(output="工具执行成功")

def create_agent():
    """Agent工厂函数 - 每个会话创建一个新的Agent实例"""
    tools = [MyTool()]
    return create_toolcall_agent(
        tools=tools,
        name="my_agent",
        description="我的智能助手"
    )

async def main():
    # 创建WebSocket服务器
    server = AgentWebSocketServer(
        agent_factory_func=create_agent,
        host="localhost",
        port=8080,
        state_secret_key="your-production-secret-key"  # 生产环境必须提供固定密钥
    )

    try:
        # 启动服务器
        await server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        await server.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

启动服务器：
```bash
uv run python my_agent_server.py
```

## 5. 测试连接

1. **运行服务器**
2. **运行客户端代码** (选择上面任一版本)
3. **查看输出** - 应该看到连接成功和会话创建的消息
4. **发送消息** - 客户端会自动发送测试消息

### 期望的输出

```
✅ 连接成功
🚀 会话创建成功: sess_abc123
💭 正在处理您的请求...
🎯 Agent回答: 你好！我是 MyAgent，一个智能助手...
```

## 6. 客户端状态管理 (可选)

如果你需要在客户端保存会话状态以便离线后恢复，可以使用状态管理功能：

### 状态导出

```javascript
// 导出当前会话状态
function exportState() {
    if (!sessionId) return;
    
    const message = {
        event: 'user.request_state',
        session_id: sessionId,
        timestamp: new Date().toISOString()
    };
    ws.send(JSON.stringify(message));
}

// 监听状态导出响应
function handleMessage(data) {
    const { event } = data;
    
    if (event === 'agent.state_exported') {
        const signedState = data.metadata?.signed_state;
        if (signedState) {
            // 保存到本地存储
            localStorage.setItem(`session_${sessionId}`, JSON.stringify(signedState));
            console.log('✅ 状态已保存');
        }
    }
}
```

### 状态恢复

```javascript
// 从本地存储恢复状态
function restoreState(originalSessionId) {
    const stateData = localStorage.getItem(`session_${originalSessionId}`);
    if (!stateData) return;
    
    const signedState = JSON.parse(stateData);
    const message = {
        event: 'user.reconnect_with_state',
        signed_state: signedState,
        timestamp: new Date().toISOString()
    };
    ws.send(JSON.stringify(message));
}

// 监听状态恢复响应
function handleMessage(data) {
    const { event } = data;
    
    if (event === 'agent.state_restored') {
        sessionId = data.session_id;
        console.log(`✅ 会话已恢复: ${sessionId}`);
        console.log(`恢复步骤: ${data.metadata?.restored_step}`);
    }
}
```

### Python 状态管理示例

```python
import json

class StateManager:
    def __init__(self, client):
        self.client = client
        self.local_states = {}
    
    async def export_state(self, session_id):
        """导出会话状态"""
        message = {
            'event': 'user.request_state',
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        await self.client.send_message(message)
    
    async def restore_state(self, signed_state):
        """恢复会话状态"""
        message = {
            'event': 'user.reconnect_with_state',
            'signed_state': signed_state,
            'timestamp': datetime.now().isoformat()
        }
        await self.client.send_message(message)
    
    def save_state_to_file(self, session_id, signed_state):
        """保存状态到文件"""
        filename = f"session_{session_id}.json"
        with open(filename, 'w') as f:
            json.dump(signed_state, f, indent=2)
        print(f"✅ 状态已保存到 {filename}")
```

## 7. 下一步

现在你已经成功建立了基本连接！接下来你可以：

- 学习 [客户端状态管理](./client-state-management.md) - 完整的状态管理功能
- 学习 [用户确认机制](./user-confirmation.md) - 处理需要用户确认的操作
- 查看 [React集成示例](./react-integration.md) - 在React应用中使用
- 了解 [数据可视化集成](./visualization-integration.md) - 图表展示功能
- 熟悉 [Plan & Solve 消息指南](./plan_solver_messages.md) - 规划/求解流水线与细粒度控制

## 故障排除

### 连接失败
- 检查服务器是否运行在正确的端口
- 确认WebSocket URL格式正确 (`ws://` 或 `wss://`)

### 消息不响应  
- 检查 session_id 是否正确设置
- 确认消息格式符合协议规范

### 服务器错误
- 查看服务器日志获取详细错误信息
- 确认Agent配置正确

如有其他问题，请查看 [基础概念文档](./basic-concepts.md) 了解更多技术细节。
