# 客户端工具确认功能集成指南

## 概述

MyAgent WebSocket 框架现在支持工具执行前的用户确认功能。当智能体需要执行危险或需要人工审核的操作时，会暂停执行并请求客户端用户确认，只有在用户明确同意后才会继续执行工具。

## 功能特性

- 🔒 **安全控制**: 危险操作执行前需要用户明确确认
- ⏱️ **超时处理**: 支持确认请求超时机制（默认 5 分钟）
- 📋 **详细信息**: 确认请求包含工具名称、描述、参数等完整信息
- 🎛️ **灵活配置**: 工具级别控制是否需要确认
- 🔄 **实时交互**: 基于 WebSocket 的实时确认流程

## WebSocket 事件协议

### 1. 确认请求事件（服务端 → 客户端）

当工具需要用户确认时，服务端发送以下事件：

```json
{
  "event": "agent.user_confirm",
  "session_id": "session_123",
  "step_id": "step_1_confirm_delete_file", 
  "timestamp": "2025-01-15T10:30:00.000Z",
  "content": "确认执行工具: delete_file",
  "metadata": {
    "tool_name": "delete_file",
    "tool_description": "删除指定的文件",
    "tool_args": {
      "filename": "/important/data.txt",
      "force": true
    },
    "requires_confirmation": true
  }
}
```

**字段说明：**
- `event`: 固定值 `"agent.user_confirm"`
- `session_id`: 会话标识符
- `step_id`: 步骤标识符，用于关联确认响应
- `content`: 确认提示信息
- `metadata.tool_name`: 需要确认的工具名称
- `metadata.tool_description`: 工具功能描述
- `metadata.tool_args`: 工具执行参数
- `metadata.requires_confirmation`: 确认标志（固定为 true）

### 2. 用户响应事件（客户端 → 服务端）

客户端需要发送以下格式的响应：

```json
{
  "event": "user.response",
  "session_id": "session_123",
  "step_id": "step_1_confirm_delete_file",
  "content": {
    "confirmed": true,
    "reason": "User approved the operation"
  }
}
```

**字段说明：**
- `event`: 固定值 `"user.response"`
- `session_id`: 对应的会话标识符
- `step_id`: 对应的步骤标识符（必须与请求中的一致）
- `content.confirmed`: 布尔值，true 表示确认，false 表示拒绝
- `content.reason`: 可选，确认或拒绝的原因说明

## 客户端实现指南

### JavaScript/Web 客户端实现

```javascript
class MyAgentClient {
    constructor(wsUrl) {
        this.ws = new WebSocket(wsUrl);
        this.sessionId = null;
        this.pendingConfirmations = new Map();
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
    }
    
    handleMessage(message) {
        switch (message.event) {
            case 'agent.session_created':
                this.sessionId = message.session_id;
                break;
                
            case 'agent.user_confirm':
                this.handleConfirmationRequest(message);
                break;
                
            case 'agent.final_answer':
                this.displayFinalAnswer(message.content);
                break;
                
            // 处理其他事件...
        }
    }
    
    handleConfirmationRequest(message) {
        const { step_id, content, metadata } = message;
        
        // 显示确认对话框
        this.showConfirmationDialog({
            stepId: step_id,
            message: content,
            toolName: metadata.tool_name,
            toolDescription: metadata.tool_description,
            toolArgs: metadata.tool_args,
            onConfirm: (confirmed, reason) => {
                this.sendConfirmation(step_id, confirmed, reason);
            }
        });
    }
    
    sendConfirmation(stepId, confirmed, reason = null) {
        const response = {
            event: "user.response",
            session_id: this.sessionId,
            step_id: stepId,
            content: {
                confirmed: confirmed,
                ...(reason && { reason: reason })
            }
        };
        
        this.ws.send(JSON.stringify(response));
    }
    
    showConfirmationDialog({ stepId, message, toolName, toolDescription, toolArgs, onConfirm }) {
        // 创建确认对话框
        const dialog = document.createElement('div');
        dialog.className = 'confirmation-dialog';
        dialog.innerHTML = `
            <div class="dialog-overlay">
                <div class="dialog-content">
                    <h3>工具执行确认</h3>
                    <p><strong>操作:</strong> ${message}</p>
                    <p><strong>工具:</strong> ${toolName}</p>
                    <p><strong>描述:</strong> ${toolDescription}</p>
                    <p><strong>参数:</strong></p>
                    <pre>${JSON.stringify(toolArgs, null, 2)}</pre>
                    
                    <div class="dialog-buttons">
                        <button class="confirm-btn" onclick="handleConfirm(true)">确认执行</button>
                        <button class="cancel-btn" onclick="handleConfirm(false)">取消</button>
                    </div>
                </div>
            </div>
        `;
        
        // 设置按钮事件处理
        window.handleConfirm = (confirmed) => {
            onConfirm(confirmed, confirmed ? '用户确认执行' : '用户取消操作');
            document.body.removeChild(dialog);
            delete window.handleConfirm;
        };
        
        document.body.appendChild(dialog);
    }
}

// 使用示例
const client = new MyAgentClient('ws://localhost:8890');
```

### React 组件实现

```jsx
import React, { useState, useEffect } from 'react';

const ConfirmationDialog = ({ request, onConfirm, onCancel }) => {
    if (!request) return null;
    
    const { message, metadata } = request;
    
    return (
        <div className="confirmation-dialog-overlay">
            <div className="confirmation-dialog">
                <h3>工具执行确认</h3>
                <div className="confirmation-content">
                    <p><strong>操作:</strong> {message}</p>
                    <p><strong>工具:</strong> {metadata.tool_name}</p>
                    <p><strong>描述:</strong> {metadata.tool_description}</p>
                    <details>
                        <summary>查看参数</summary>
                        <pre>{JSON.stringify(metadata.tool_args, null, 2)}</pre>
                    </details>
                </div>
                <div className="dialog-buttons">
                    <button 
                        className="confirm-button"
                        onClick={() => onConfirm(true, '用户确认执行')}
                    >
                        确认执行
                    </button>
                    <button 
                        className="cancel-button"
                        onClick={() => onConfirm(false, '用户取消操作')}
                    >
                        取消
                    </button>
                </div>
            </div>
        </div>
    );
};

const MyAgentChat = () => {
    const [ws, setWs] = useState(null);
    const [sessionId, setSessionId] = useState(null);
    const [confirmationRequest, setConfirmationRequest] = useState(null);
    const [messages, setMessages] = useState([]);
    
    useEffect(() => {
        const websocket = new WebSocket('ws://localhost:8890');
        
        websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            handleMessage(message);
        };
        
        setWs(websocket);
        
        return () => websocket.close();
    }, []);
    
    const handleMessage = (message) => {
        switch (message.event) {
            case 'agent.session_created':
                setSessionId(message.session_id);
                break;
                
            case 'agent.user_confirm':
                setConfirmationRequest(message);
                break;
                
            case 'agent.final_answer':
                setMessages(prev => [...prev, {
                    type: 'agent',
                    content: message.content
                }]);
                break;
        }
    };
    
    const handleConfirmation = (confirmed, reason) => {
        if (!confirmationRequest || !ws || !sessionId) return;
        
        const response = {
            event: "user.response",
            session_id: sessionId,
            step_id: confirmationRequest.step_id,
            content: {
                confirmed: confirmed,
                reason: reason
            }
        };
        
        ws.send(JSON.stringify(response));
        setConfirmationRequest(null);
    };
    
    return (
        <div className="chat-container">
            {/* 聊天界面 */}
            <div className="messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.type}`}>
                        {msg.content}
                    </div>
                ))}
            </div>
            
            {/* 确认对话框 */}
            <ConfirmationDialog
                request={confirmationRequest}
                onConfirm={handleConfirmation}
            />
        </div>
    );
};

export default MyAgentChat;
```

### Python 客户端实现

```python
import asyncio
import json
import websockets
from typing import Dict, Any, Callable, Optional

class MyAgentClient:
    def __init__(self, ws_url: str, confirmation_handler: Optional[Callable] = None):
        self.ws_url = ws_url
        self.session_id: Optional[str] = None
        self.confirmation_handler = confirmation_handler or self.default_confirmation_handler
        
    async def connect(self):
        """连接到 WebSocket 服务器"""
        self.ws = await websockets.connect(self.ws_url)
        
        # 启动消息处理循环
        await asyncio.gather(
            self.message_handler(),
            self.create_session()
        )
    
    async def message_handler(self):
        """处理接收到的消息"""
        async for message in self.ws:
            try:
                data = json.loads(message)
                await self.handle_message(data)
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
    
    async def handle_message(self, message: Dict[str, Any]):
        """处理不同类型的消息"""
        event = message.get("event")
        
        if event == "agent.session_created":
            self.session_id = message.get("session_id")
            print(f"Session created: {self.session_id}")
            
        elif event == "agent.user_confirm":
            await self.handle_confirmation_request(message)
            
        elif event == "agent.final_answer":
            print(f"Agent: {message.get('content')}")
    
    async def handle_confirmation_request(self, message: Dict[str, Any]):
        """处理确认请求"""
        step_id = message.get("step_id")
        content = message.get("content")
        metadata = message.get("metadata", {})
        
        # 调用确认处理器
        confirmed, reason = await self.confirmation_handler(
            step_id=step_id,
            message=content,
            tool_name=metadata.get("tool_name"),
            tool_description=metadata.get("tool_description"),
            tool_args=metadata.get("tool_args")
        )
        
        # 发送确认响应
        await self.send_confirmation(step_id, confirmed, reason)
    
    async def default_confirmation_handler(self, step_id: str, message: str, 
                                         tool_name: str, tool_description: str, 
                                         tool_args: Dict[str, Any]) -> tuple[bool, str]:
        """默认的确认处理器（命令行交互）"""
        print(f"\n=== 工具执行确认 ===")
        print(f"消息: {message}")
        print(f"工具: {tool_name}")
        print(f"描述: {tool_description}")
        print(f"参数: {json.dumps(tool_args, indent=2, ensure_ascii=False)}")
        
        while True:
            response = input("是否确认执行? (y/n): ").strip().lower()
            if response == 'y':
                return True, "用户确认执行"
            elif response == 'n':
                return False, "用户拒绝执行"
            else:
                print("请输入 'y' 或 'n'")
    
    async def send_confirmation(self, step_id: str, confirmed: bool, reason: str = None):
        """发送确认响应"""
        response = {
            "event": "user.response",
            "session_id": self.session_id,
            "step_id": step_id,
            "content": {
                "confirmed": confirmed
            }
        }
        
        if reason:
            response["content"]["reason"] = reason
            
        await self.ws.send(json.dumps(response))
    
    async def send_message(self, content: str):
        """发送用户消息"""
        if not self.session_id:
            print("Session not created yet")
            return
            
        message = {
            "event": "user.message",
            "session_id": self.session_id,
            "content": content
        }
        
        await self.ws.send(json.dumps(message))
    
    async def create_session(self):
        """创建会话"""
        message = {
            "event": "user.create_session",
            "content": "Create new session"
        }
        
        await self.ws.send(json.dumps(message))

# 使用示例
async def main():
    # 自定义确认处理器
    async def custom_confirmation_handler(step_id, message, tool_name, tool_description, tool_args):
        # 这里可以实现 GUI 对话框或其他交互方式
        print(f"Custom confirmation for {tool_name}: {message}")
        return True, "Auto-approved"
    
    client = MyAgentClient(
        "ws://localhost:8890",
        confirmation_handler=custom_confirmation_handler
    )
    
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
```

## 最佳实践

### 1. 用户体验设计

- **清晰的确认界面**: 显示工具名称、描述和参数信息
- **操作风险提示**: 对危险操作使用醒目的视觉提示
- **超时处理**: 提供倒计时显示和超时提醒
- **操作日志**: 记录用户的确认/拒绝操作

### 2. 错误处理

```javascript
handleConfirmationTimeout(stepId) {
    // 清理待确认状态
    this.pendingConfirmations.delete(stepId);
    
    // 显示超时提醒
    this.showNotification('确认请求已超时', 'warning');
}

handleConfirmationError(error) {
    console.error('Confirmation error:', error);
    this.showNotification('确认处理出错，请重试', 'error');
}
```

### 3. 安全考虑

- **参数验证**: 检查确认请求中的参数是否合理
- **会话验证**: 确保 step_id 和 session_id 匹配
- **用户身份**: 在敏感操作前验证用户身份
- **审计日志**: 记录所有确认操作用于审计

### 4. 国际化支持

```javascript
const confirmationMessages = {
    'zh-CN': {
        title: '工具执行确认',
        confirm: '确认执行',
        cancel: '取消',
        timeout: '确认请求已超时'
    },
    'en-US': {
        title: 'Tool Execution Confirmation',
        confirm: 'Confirm',
        cancel: 'Cancel',
        timeout: 'Confirmation request timed out'
    }
};
```

## 常见问题

### Q: 如何处理网络中断时的确认状态？
A: 客户端重连后应清理所有待确认状态，服务端会自动超时处理未响应的确认请求。

### Q: 可以自定义确认超时时间吗？
A: 当前超时时间为 5 分钟，如需自定义可在服务端配置中修改 `confirmation_timeout` 参数。

### Q: 如何实现批量确认？
A: 每个工具调用都会单独发送确认请求，客户端需要逐个处理。未来版本可能支持批量确认。

### Q: 确认被拒绝后会发生什么？
A: 工具不会执行，Agent 会收到 "Tool execution cancelled by user" 错误并继续其他操作。

## 测试工具

框架提供了完整的测试示例：

- **服务端示例**: `examples/ws_confirmation_demo.py`
- **Web 客户端**: `examples/confirmation_client.html`
- **测试命令**: 
  ```bash
  # 启动测试服务器
  uv run python examples/ws_confirmation_demo.py
  
  # 在浏览器中打开客户端
  open examples/confirmation_client.html
  ```

通过这些示例，您可以快速了解和测试工具确认功能的完整流程。