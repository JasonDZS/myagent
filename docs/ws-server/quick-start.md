# MyAgent WebSocket 一键部署 - 快速开始

## 🚀 5分钟快速部署

### 1. 安装依赖

```bash
# 安装 WebSocket 服务器依赖
pip install -r requirements-ws.txt

# 或者单独安装核心依赖
pip install websockets pydantic openai python-dotenv
```

### 2. 创建你的 Agent 文件

```python
# my_agent.py
from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult

class HelloTool(BaseTool):
    name = "say_hello"
    description = "向用户打招呼"
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "用户名称"}
        },
        "required": ["name"]
    }
    
    async def execute(self, name: str) -> ToolResult:
        return ToolResult(output=f"你好, {name}! 很高兴认识你！")

# 必须命名为 'agent'
agent = create_react_agent(
    name="hello-assistant",
    tools=[HelloTool()],
    system_prompt="你是一个友好的助手",
    max_steps=3
)
```

### 3. 一键启动服务

```bash
# 使用 Python 模块方式启动
python -m myagent.cli.server my_agent.py --host 0.0.0.0 --port 8080

# 或使用脚本启动
./scripts/myagent-ws server my_agent.py --host 0.0.0.0 --port 8080
```

### 4. 测试连接

```javascript
// 前端 JavaScript 客户端测试
const ws = new WebSocket('ws://localhost:8080');

ws.onopen = () => {
    console.log('已连接到 MyAgent');
    // 创建会话
    ws.send(JSON.stringify({
        event: 'user.create_session',
        timestamp: new Date().toISOString()
    }));
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    console.log('收到消息:', msg);
    
    if (msg.event === 'agent.session_created') {
        // 发送用户消息
        ws.send(JSON.stringify({
            event: 'user.message',
            session_id: msg.session_id,
            content: '你好！',
            timestamp: new Date().toISOString()
        }));
    }
};
```

## 🎯 完整示例

### 天气助手 Agent

我们已经为您准备了一个完整的天气助手示例：

```bash
# 运行天气助手示例
python -m myagent.cli.server examples/ws_weather_agent.py --host 0.0.0.0 --port 8080
```

这个示例包含：
- 天气查询工具
- 城市信息查询工具  
- 完整的错误处理
- 异步执行支持

### 测试天气助手

```bash
# 服务启动后，访问 ws://localhost:8080
# 发送以下消息测试：

# 1. 创建会话
{
  "event": "user.create_session",
  "timestamp": "2024-01-01T12:00:00Z"
}

# 2. 查询天气
{
  "event": "user.message", 
  "session_id": "your-session-id",
  "content": "北京今天天气怎么样？",
  "timestamp": "2024-01-01T12:01:00Z"
}

# 3. 查询城市信息
{
  "event": "user.message",
  "session_id": "your-session-id", 
  "content": "告诉我上海的基本信息",
  "timestamp": "2024-01-01T12:02:00Z"
}
```

## 📋 Agent 文件规范

### 基本结构

```python
from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult

# 1. 定义工具类
class YourTool(BaseTool):
    name = "tool_name"
    description = "工具描述"
    parameters = {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "参数描述"}
        },
        "required": ["param"]
    }
    
    async def execute(self, param: str) -> ToolResult:
        # 工具逻辑
        return ToolResult(output="结果")

# 2. 创建 Agent (必须命名为 'agent')
agent = create_react_agent(
    name="your-agent",
    tools=[YourTool()],
    system_prompt="系统提示",
    max_steps=5
)
```

### 高级配置

```python
agent = create_react_agent(
    name="advanced-agent",
    tools=[Tool1(), Tool2(), Tool3()],
    system_prompt="详细的系统提示...",
    next_step_prompt="下一步操作提示...", 
    max_steps=10,
    enable_tracing=True,  # 启用执行追踪
    # 可以添加更多配置
)
```

## 🔧 命令行选项

### 基本用法

```bash
myagent-ws server <agent_file> [options]
```

### 可用选项

- `--host` : 服务器主机地址 (默认: localhost)
- `--port` : 服务器端口 (默认: 8080)  
- `--debug` : 启用调试模式

### 示例

```bash
# 基本启动
myagent-ws server my_agent.py

# 指定主机和端口
myagent-ws server my_agent.py --host 0.0.0.0 --port 9000

# 启用调试模式
myagent-ws server my_agent.py --debug

# 查看帮助
myagent-ws --help
myagent-ws server --help
```

## 🌐 WebSocket 事件协议

### 用户事件

```javascript
// 创建会话
{
    "event": "user.create_session",
    "timestamp": "ISO-8601-timestamp"
}

// 发送消息  
{
    "event": "user.message",
    "session_id": "session-uuid",
    "content": "用户消息内容",
    "timestamp": "ISO-8601-timestamp"
}

// 取消操作
{
    "event": "user.cancel", 
    "session_id": "session-uuid",
    "timestamp": "ISO-8601-timestamp"
}
```

### Agent 响应事件

```javascript
// 会话创建成功
{
    "event": "agent.session_created",
    "session_id": "session-uuid",
    "content": "会话创建成功",
    "timestamp": "...",
    "metadata": {
        "agent_name": "agent-name",
        "connection_id": "connection-uuid"
    }
}

// Agent 思考中
{
    "event": "agent.thinking",
    "session_id": "session-uuid", 
    "content": "正在分析您的问题...",
    "metadata": {"step": 1}
}

// 工具调用
{
    "event": "agent.tool_call",
    "session_id": "session-uuid",
    "step_id": "step-uuid",
    "content": "调用工具: tool_name",
    "metadata": {
        "tool": "tool_name",
        "args": {...},
        "status": "running"
    }
}

// 工具结果
{
    "event": "agent.tool_result",
    "session_id": "session-uuid",
    "step_id": "step-uuid", 
    "content": "工具执行结果",
    "metadata": {
        "tool": "tool_name",
        "status": "success"
    }
}

// 最终回答
{
    "event": "agent.final_answer",
    "session_id": "session-uuid",
    "content": "最终回答内容",
    "timestamp": "..."
}

// 错误事件
{
    "event": "agent.error",
    "session_id": "session-uuid",
    "content": "错误描述",
    "timestamp": "..."
}
```

## 🐛 故障排除

### 常见问题

**1. Agent 文件加载失败**
```
❌ 在 my_agent.py 中未找到 'agent' 变量
```
解决方案：确保文件中定义了名为 `agent` 的变量

**2. 端口占用**
```
❌ 服务器错误: [Errno 48] Address already in use
```
解决方案：更换端口或停止占用端口的进程

**3. WebSocket 连接失败**
- 检查防火墙设置
- 确认服务器正在运行
- 验证 host 和 port 配置

**4. Agent 执行超时**
- 检查工具实现是否有死循环
- 增加 max_steps 限制
- 检查网络连接（如使用外部 API）

### 调试模式

```bash
# 启用详细日志
myagent-ws server my_agent.py --debug

# 查看 Agent 执行过程
python -c "
import asyncio
from my_agent import agent
asyncio.run(agent.arun('测试消息'))
"
```

## 📚 更多资源

- [完整技术文档](backend-deployment.md)
- [WebSocket 通信协议设计](design.md)
- [Agent 开发指南](../../../README.md)
- [示例代码](../../examples/)

## 🆘 获取帮助

如遇问题，请：

1. 检查上述故障排除指南
2. 查看完整技术文档
3. 运行 `myagent-ws --help` 查看命令帮助
4. 在 GitHub 仓库提交 Issue