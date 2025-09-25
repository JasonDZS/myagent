# 工具确认功能快速开始指南

## 5分钟快速集成

### 第一步：创建需要确认的工具

```python
# server_agent.py
from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult

class DangerousTool(BaseTool):
    name: str = "delete_database"
    description: str = "删除数据库"
    user_confirm: bool = True  # 启用用户确认
    parameters = {
        "type": "object",
        "properties": {
            "database_name": {"type": "string", "description": "数据库名称"}
        },
        "required": ["database_name"]
    }
    
    async def execute(self, database_name: str):
        return ToolResult(output=f"数据库 {database_name} 已删除")

def create_agent():
    return create_react_agent([DangerousTool()])
```

### 第二步：启动WebSocket服务器

```bash
# 启动服务器
uv run python -m myagent.cli.server server server_agent.py --port 8890
```

### 第三步：集成客户端确认处理

#### 方案A：JavaScript/Web 客户端

```html
<!DOCTYPE html>
<html>
<head>
    <title>快速集成示例</title>
</head>
<body>
    <div id="chat"></div>
    <input type="text" id="input" placeholder="输入消息...">
    <button onclick="sendMessage()">发送</button>

    <script>
        const ws = new WebSocket('ws://localhost:8890');
        let sessionId = null;
        
        ws.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            
            if (msg.event === 'agent.session_created') {
                sessionId = msg.session_id;
            }
            
            // 处理确认请求
            if (msg.event === 'agent.user_confirm') {
                const confirmed = confirm(`确认执行: ${msg.content}`);
                
                ws.send(JSON.stringify({
                    event: 'user.response',
                    session_id: sessionId,
                    step_id: msg.step_id,
                    content: { confirmed }
                }));
            }
            
            // 显示其他消息
            if (msg.content) {
                document.getElementById('chat').innerHTML += 
                    `<p>${msg.event}: ${msg.content}</p>`;
            }
        };
        
        ws.onopen = () => {
            ws.send(JSON.stringify({
                event: 'user.create_session',
                content: 'create session'
            }));
        };
        
        function sendMessage() {
            const input = document.getElementById('input');
            ws.send(JSON.stringify({
                event: 'user.message',
                session_id: sessionId,
                content: input.value
            }));
            input.value = '';
        }
    </script>
</body>
</html>
```

#### 方案B：Python 命令行客户端

```python
# client.py
import asyncio
import json
import websockets

class SimpleClient:
    def __init__(self):
        self.ws = None
        self.session_id = None
    
    async def connect(self):
        self.ws = await websockets.connect('ws://localhost:8890')
        
        # 创建会话
        await self.ws.send(json.dumps({
            'event': 'user.create_session',
            'content': 'create session'
        }))
        
        # 监听消息
        async for message in self.ws:
            data = json.loads(message)
            await self.handle_message(data)
    
    async def handle_message(self, msg):
        if msg['event'] == 'agent.session_created':
            self.session_id = msg['session_id']
            print("会话已创建，输入消息开始对话...")
            
            # 启动输入处理
            asyncio.create_task(self.input_handler())
        
        elif msg['event'] == 'agent.user_confirm':
            # 处理确认请求
            print(f"\n确认请求: {msg['content']}")
            print(f"工具: {msg['metadata']['tool_name']}")
            
            response = input("确认执行? (y/n): ")
            confirmed = response.lower() == 'y'
            
            await self.ws.send(json.dumps({
                'event': 'user.response',
                'session_id': self.session_id,
                'step_id': msg['step_id'],
                'content': {'confirmed': confirmed}
            }))
        
        elif msg.get('content'):
            print(f"{msg['event']}: {msg['content']}")
    
    async def input_handler(self):
        while True:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, input, "You: "
            )
            
            await self.ws.send(json.dumps({
                'event': 'user.message',
                'session_id': self.session_id,
                'content': user_input
            }))

if __name__ == '__main__':
    client = SimpleClient()
    asyncio.run(client.connect())
```

### 第四步：测试确认流程

1. 打开客户端
2. 发送消息：`"请删除test_db数据库"`
3. 应该会收到确认请求
4. 选择确认或取消
5. 查看工具执行结果

## 进阶自定义

### 自定义确认界面

```javascript
// 美化的确认对话框
function showConfirmationDialog(request) {
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background: white; border: 2px solid #ff6b6b; border-radius: 8px;
        padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;
    `;
    
    dialog.innerHTML = `
        <h3 style="color: #ff6b6b; margin-top: 0;">⚠️ 危险操作确认</h3>
        <p><strong>操作:</strong> ${request.content}</p>
        <p><strong>工具:</strong> ${request.metadata.tool_name}</p>
        <div style="margin-top: 20px; text-align: right;">
            <button id="cancelBtn" style="margin-right: 10px; background: #ddd;">取消</button>
            <button id="confirmBtn" style="background: #ff6b6b; color: white;">确认执行</button>
        </div>
    `;
    
    document.body.appendChild(dialog);
    
    document.getElementById('confirmBtn').onclick = () => {
        sendConfirmation(request.step_id, true);
        document.body.removeChild(dialog);
    };
    
    document.getElementById('cancelBtn').onclick = () => {
        sendConfirmation(request.step_id, false);
        document.body.removeChild(dialog);
    };
}
```

### 添加用户身份验证

```python
class SecureTool(BaseTool):
    name: str = "admin_operation"
    description: str = "管理员操作"
    user_confirm: bool = True
    
    async def execute(self, operation: str):
        # 检查用户权限（需要在确认时传递用户信息）
        return ToolResult(output=f"执行管理操作: {operation}")

# 客户端发送用户信息
{
    "event": "user.response",
    "session_id": "sess_123",
    "step_id": "step_1",
    "content": {
        "confirmed": true,
        "user_id": "admin_user",
        "reason": "管理员确认执行"
    }
}
```

### 批量操作确认

```python
class BatchTool(BaseTool):
    name: str = "batch_delete"
    description: str = "批量删除文件"
    user_confirm: bool = True
    
    async def execute(self, files: list[str]):
        # 显示将要删除的所有文件
        return ToolResult(output=f"删除了 {len(files)} 个文件")

# 工具参数会显示在确认对话框中
# {
#   "tool_args": {
#     "files": ["file1.txt", "file2.txt", "file3.txt"]
#   }
# }
```

## 常见问题解决

### Q: 确认对话框没有出现？
```javascript
// 检查事件监听
ws.onmessage = function(event) {
    const msg = JSON.parse(event.data);
    console.log('Received:', msg); // 调试输出
    
    if (msg.event === 'agent.user_confirm') {
        // 确保这里的代码会执行
        console.log('Confirmation requested');
        handleConfirmation(msg);
    }
};
```

### Q: 确认后没有反应？
```javascript
// 确保 step_id 正确
function sendConfirmation(stepId, confirmed) {
    const response = {
        event: 'user.response',
        session_id: sessionId,  // 确保 sessionId 不为空
        step_id: stepId,        // 确保 stepId 匹配
        content: { confirmed }
    };
    
    console.log('Sending:', response); // 调试输出
    ws.send(JSON.stringify(response));
}
```

### Q: 工具确认设置没生效？
```python
# 确保工具正确配置
class MyTool(BaseTool):
    name: str = "my_tool"          # 必须有类型注解
    description: str = "My tool"   # 必须有类型注解
    user_confirm: bool = True      # 必须有类型注解
    
    async def execute(self, **kwargs):
        return ToolResult(output="success")
```

## 生产环境部署

### 安全配置
```python
# 生产环境建议配置
class ProductionTool(BaseTool):
    name: str = "production_deploy"
    description: str = "生产环境部署"
    user_confirm: bool = True
    
    async def execute(self, **kwargs):
        # 添加额外安全检查
        if not self.verify_production_access():
            return ToolResult(error="无生产环境访问权限")
        
        return ToolResult(output="部署成功")
    
    def verify_production_access(self):
        # 实现权限验证逻辑
        return True
```

### 审计日志
```javascript
// 记录所有确认操作
function sendConfirmation(stepId, confirmed, reason) {
    // 发送确认
    ws.send(JSON.stringify({
        event: 'user.response',
        session_id: sessionId,
        step_id: stepId,
        content: { confirmed, reason }
    }));
    
    // 记录审计日志
    logAuditEvent({
        timestamp: new Date().toISOString(),
        action: 'tool_confirmation',
        stepId,
        confirmed,
        reason,
        userId: getCurrentUserId()
    });
}
```

现在您可以在几分钟内快速集成工具确认功能！记住要根据实际需求调整确认界面和安全策略。