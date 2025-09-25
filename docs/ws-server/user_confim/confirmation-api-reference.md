# 工具确认功能 API 参考

## WebSocket 事件规范

### 事件类型常量

```javascript
const UserEvents = {
    MESSAGE: "user.message",
    RESPONSE: "user.response",
    CANCEL: "user.cancel",
    CREATE_SESSION: "user.create_session",
    RECONNECT: "user.reconnect"
};

const AgentEvents = {
    THINKING: "agent.thinking",
    TOOL_CALL: "agent.tool_call", 
    TOOL_RESULT: "agent.tool_result",
    PARTIAL_ANSWER: "agent.partial_answer",
    FINAL_ANSWER: "agent.final_answer",
    USER_CONFIRM: "agent.user_confirm",    // 确认请求事件
    ERROR: "agent.error",
    TIMEOUT: "agent.timeout",
    INTERRUPTED: "agent.interrupted",
    SESSION_CREATED: "agent.session_created",
    SESSION_END: "agent.session_end"
};
```

## 事件详细规范

### 1. agent.user_confirm (服务端 → 客户端)

**描述**: 当工具需要用户确认时发送此事件

**事件结构**:
```typescript
interface UserConfirmEvent {
    event: "agent.user_confirm";
    session_id: string;
    step_id: string;
    timestamp: string;      // ISO 8601 格式
    connection_id?: string;
    content: string;        // 确认提示消息
    metadata: {
        tool_name: string;           // 工具名称
        tool_description: string;    // 工具描述
        tool_args: Record<string, any>; // 工具参数
        requires_confirmation: true; // 固定为 true
        [key: string]: any;         // 其他元数据
    };
}
```

**示例**:
```json
{
    "event": "agent.user_confirm",
    "session_id": "sess_abc123",
    "step_id": "step_5_confirm_delete_file",
    "timestamp": "2025-01-15T14:30:25.123Z",
    "content": "确认执行工具: delete_file",
    "metadata": {
        "tool_name": "delete_file",
        "tool_description": "删除指定的文件",
        "tool_args": {
            "filename": "/important/database.sql",
            "force": true,
            "backup": false
        },
        "requires_confirmation": true
    }
}
```

### 2. user.response (客户端 → 服务端)

**描述**: 客户端对确认请求的响应

**事件结构**:
```typescript
interface UserResponseEvent {
    event: "user.response";
    session_id: string;
    step_id: string;        // 必须与确认请求中的 step_id 一致
    timestamp?: string;     // 可选，客户端时间戳
    content: {
        confirmed: boolean;     // true=确认, false=拒绝
        reason?: string;        // 可选，确认/拒绝的原因
        user_id?: string;       // 可选，执行确认的用户ID
        metadata?: Record<string, any>; // 可选，额外元数据
    };
}
```

**确认示例**:
```json
{
    "event": "user.response",
    "session_id": "sess_abc123",
    "step_id": "step_5_confirm_delete_file",
    "timestamp": "2025-01-15T14:31:10.456Z",
    "content": {
        "confirmed": true,
        "reason": "用户确认删除文件",
        "user_id": "user_123"
    }
}
```

**拒绝示例**:
```json
{
    "event": "user.response", 
    "session_id": "sess_abc123",
    "step_id": "step_5_confirm_delete_file",
    "timestamp": "2025-01-15T14:31:05.789Z",
    "content": {
        "confirmed": false,
        "reason": "文件太重要，不能删除"
    }
}
```

## 客户端 SDK

### TypeScript/JavaScript SDK

```typescript
interface ConfirmationRequest {
    stepId: string;
    message: string;
    toolName: string;
    toolDescription: string;
    toolArgs: Record<string, any>;
}

interface ConfirmationResponse {
    confirmed: boolean;
    reason?: string;
    userId?: string;
    metadata?: Record<string, any>;
}

class MyAgentConfirmationHandler {
    private ws: WebSocket;
    private sessionId: string | null = null;
    private pendingConfirmations = new Map<string, ConfirmationRequest>();
    
    constructor(wsUrl: string) {
        this.ws = new WebSocket(wsUrl);
        this.setupEventHandlers();
    }
    
    private setupEventHandlers(): void {
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
    }
    
    private handleMessage(message: any): void {
        switch (message.event) {
            case 'agent.session_created':
                this.sessionId = message.session_id;
                break;
                
            case 'agent.user_confirm':
                this.handleConfirmationRequest(message);
                break;
        }
    }
    
    private handleConfirmationRequest(message: any): void {
        const request: ConfirmationRequest = {
            stepId: message.step_id,
            message: message.content,
            toolName: message.metadata.tool_name,
            toolDescription: message.metadata.tool_description,
            toolArgs: message.metadata.tool_args
        };
        
        this.pendingConfirmations.set(message.step_id, request);
        this.onConfirmationRequested(request);
    }
    
    // 子类需要实现此方法
    protected onConfirmationRequested(request: ConfirmationRequest): void {
        throw new Error("Must implement onConfirmationRequested");
    }
    
    public sendConfirmation(stepId: string, response: ConfirmationResponse): void {
        if (!this.sessionId) {
            throw new Error("Session not established");
        }
        
        const message = {
            event: "user.response",
            session_id: this.sessionId,
            step_id: stepId,
            content: response
        };
        
        this.ws.send(JSON.stringify(message));
        this.pendingConfirmations.delete(stepId);
    }
    
    public getPendingConfirmation(stepId: string): ConfirmationRequest | undefined {
        return this.pendingConfirmations.get(stepId);
    }
    
    public getPendingConfirmations(): ConfirmationRequest[] {
        return Array.from(this.pendingConfirmations.values());
    }
}

// 具体实现示例
class WebConfirmationHandler extends MyAgentConfirmationHandler {
    protected onConfirmationRequested(request: ConfirmationRequest): void {
        this.showConfirmationDialog(request);
    }
    
    private showConfirmationDialog(request: ConfirmationRequest): void {
        // 创建模态对话框
        const dialog = this.createDialogElement(request);
        document.body.appendChild(dialog);
        
        // 设置按钮事件
        const confirmBtn = dialog.querySelector('.confirm-btn') as HTMLButtonElement;
        const cancelBtn = dialog.querySelector('.cancel-btn') as HTMLButtonElement;
        
        confirmBtn.onclick = () => {
            this.sendConfirmation(request.stepId, {
                confirmed: true,
                reason: "用户确认执行"
            });
            document.body.removeChild(dialog);
        };
        
        cancelBtn.onclick = () => {
            this.sendConfirmation(request.stepId, {
                confirmed: false,
                reason: "用户取消操作"
            });
            document.body.removeChild(dialog);
        };
    }
    
    private createDialogElement(request: ConfirmationRequest): HTMLElement {
        const dialog = document.createElement('div');
        dialog.className = 'confirmation-dialog';
        dialog.innerHTML = `
            <div class="dialog-backdrop">
                <div class="dialog-panel">
                    <h3>确认工具执行</h3>
                    <p><strong>操作:</strong> ${request.message}</p>
                    <p><strong>工具:</strong> ${request.toolName}</p>
                    <p><strong>描述:</strong> ${request.toolDescription}</p>
                    <details>
                        <summary>查看参数</summary>
                        <pre>${JSON.stringify(request.toolArgs, null, 2)}</pre>
                    </details>
                    <div class="dialog-actions">
                        <button class="confirm-btn">确认执行</button>
                        <button class="cancel-btn">取消</button>
                    </div>
                </div>
            </div>
        `;
        return dialog;
    }
}
```

### Python SDK

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable
import asyncio
import json
import websockets
from dataclasses import dataclass

@dataclass
class ConfirmationRequest:
    step_id: str
    message: str
    tool_name: str
    tool_description: str
    tool_args: Dict[str, Any]

@dataclass 
class ConfirmationResponse:
    confirmed: bool
    reason: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MyAgentConfirmationHandler(ABC):
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.session_id: Optional[str] = None
        self.pending_confirmations: Dict[str, ConfirmationRequest] = {}
    
    async def connect(self):
        """连接到 WebSocket 服务器"""
        self.ws = await websockets.connect(self.ws_url)
        await self._start_message_loop()
    
    async def _start_message_loop(self):
        """启动消息处理循环"""
        async for message in self.ws:
            try:
                data = json.loads(message)
                await self._handle_message(data)
            except json.JSONDecodeError:
                print(f"Invalid JSON: {message}")
    
    async def _handle_message(self, message: Dict[str, Any]):
        """处理接收到的消息"""
        event = message.get("event")
        
        if event == "agent.session_created":
            self.session_id = message.get("session_id")
            
        elif event == "agent.user_confirm":
            await self._handle_confirmation_request(message)
    
    async def _handle_confirmation_request(self, message: Dict[str, Any]):
        """处理确认请求"""
        metadata = message.get("metadata", {})
        request = ConfirmationRequest(
            step_id=message.get("step_id"),
            message=message.get("content"),
            tool_name=metadata.get("tool_name"),
            tool_description=metadata.get("tool_description"),
            tool_args=metadata.get("tool_args", {})
        )
        
        self.pending_confirmations[request.step_id] = request
        await self.on_confirmation_requested(request)
    
    @abstractmethod
    async def on_confirmation_requested(self, request: ConfirmationRequest):
        """子类需要实现此方法来处理确认请求"""
        pass
    
    async def send_confirmation(self, step_id: str, response: ConfirmationResponse):
        """发送确认响应"""
        if not self.session_id or not self.ws:
            raise RuntimeError("Session not established")
        
        message = {
            "event": "user.response",
            "session_id": self.session_id,
            "step_id": step_id,
            "content": {
                "confirmed": response.confirmed
            }
        }
        
        if response.reason:
            message["content"]["reason"] = response.reason
        if response.user_id:
            message["content"]["user_id"] = response.user_id
        if response.metadata:
            message["content"]["metadata"] = response.metadata
        
        await self.ws.send(json.dumps(message))
        self.pending_confirmations.pop(step_id, None)

# 命令行实现示例
class CliConfirmationHandler(MyAgentConfirmationHandler):
    async def on_confirmation_requested(self, request: ConfirmationRequest):
        """命令行确认处理"""
        print(f"\n{'='*50}")
        print(f"工具执行确认")
        print(f"{'='*50}")
        print(f"消息: {request.message}")
        print(f"工具: {request.tool_name}")
        print(f"描述: {request.tool_description}")
        print(f"参数: {json.dumps(request.tool_args, indent=2, ensure_ascii=False)}")
        print(f"{'='*50}")
        
        while True:
            response = input("是否确认执行? (y/n): ").strip().lower()
            if response == 'y':
                await self.send_confirmation(request.step_id, ConfirmationResponse(
                    confirmed=True,
                    reason="用户确认执行"
                ))
                break
            elif response == 'n':
                await self.send_confirmation(request.step_id, ConfirmationResponse(
                    confirmed=False,
                    reason="用户拒绝执行"
                ))
                break
            else:
                print("请输入 'y' 或 'n'")

# GUI 实现示例 (使用 tkinter)
import tkinter as tk
from tkinter import messagebox
import threading

class GuiConfirmationHandler(MyAgentConfirmationHandler):
    def __init__(self, ws_url: str):
        super().__init__(ws_url)
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏主窗口
    
    async def on_confirmation_requested(self, request: ConfirmationRequest):
        """GUI 确认处理"""
        # 在主线程中显示对话框
        future = asyncio.Future()
        
        def show_dialog():
            result = messagebox.askyesno(
                "工具执行确认",
                f"工具: {request.tool_name}\n"
                f"描述: {request.tool_description}\n"
                f"参数: {json.dumps(request.tool_args, ensure_ascii=False)}\n\n"
                f"是否确认执行?"
            )
            future.set_result(result)
        
        # 在主线程中执行 GUI 操作
        self.root.after(0, show_dialog)
        
        # 等待用户响应
        confirmed = await future
        
        await self.send_confirmation(request.step_id, ConfirmationResponse(
            confirmed=confirmed,
            reason="用户确认执行" if confirmed else "用户拒绝执行"
        ))
```

## 错误处理规范

### 错误类型

```typescript
interface ConfirmationError {
    error_type: 'timeout' | 'invalid_step_id' | 'session_not_found' | 'network_error';
    message: string;
    step_id?: string;
    timestamp: string;
}
```

### 常见错误场景

1. **超时错误**: 用户未在指定时间内响应
```json
{
    "event": "agent.error",
    "session_id": "sess_abc123", 
    "content": "User confirmation timeout",
    "metadata": {
        "error_type": "confirmation_timeout",
        "step_id": "step_5_confirm_delete_file",
        "timeout_seconds": 300
    }
}
```

2. **无效步骤ID**: 客户端发送了无效的步骤ID
```json
{
    "event": "system.error",
    "session_id": "sess_abc123",
    "content": "Invalid step_id in user response",
    "metadata": {
        "error_type": "invalid_step_id",
        "received_step_id": "invalid_step_123"
    }
}
```

3. **会话不存在**: 会话已过期或不存在
```json
{
    "event": "system.error",
    "session_id": "sess_abc123",
    "content": "Session not found",
    "metadata": {
        "error_type": "session_not_found"
    }
}
```

### 错误处理最佳实践

```javascript
class ErrorHandlingConfirmationClient {
    handleConfirmationError(error) {
        switch (error.error_type) {
            case 'timeout':
                this.showTimeoutMessage(error);
                this.clearPendingConfirmation(error.step_id);
                break;
                
            case 'invalid_step_id':
                console.error('Invalid step ID:', error);
                this.clearAllPendingConfirmations();
                break;
                
            case 'session_not_found':
                this.handleSessionExpired();
                break;
                
            case 'network_error':
                this.handleNetworkError(error);
                break;
        }
    }
    
    showTimeoutMessage(error) {
        const message = `确认请求已超时 (${error.timeout_seconds}秒)`;
        this.showNotification(message, 'warning');
    }
    
    handleSessionExpired() {
        this.clearAllPendingConfirmations();
        this.showNotification('会话已过期，请重新连接', 'error');
        this.reconnect();
    }
}
```

## 配置参数

### 服务端配置

```python
# 在 AgentSession 中可配置的参数
CONFIRMATION_TIMEOUT = 300  # 确认超时时间(秒)，默认5分钟
CONFIRMATION_RETRY_LIMIT = 3  # 重试限制
CONFIRMATION_BATCH_SIZE = 1   # 批量确认大小(当前仅支持1)
```

### 客户端配置

```javascript
const config = {
    confirmationTimeout: 300000,  // 客户端超时时间(毫秒)
    autoReconnect: true,          // 断线自动重连
    reconnectInterval: 3000,      // 重连间隔(毫秒)
    maxReconnectAttempts: 5,      // 最大重连次数
    showDetailedErrors: true      // 显示详细错误信息
};
```

这份API参考文档提供了完整的技术规范和实现指南，帮助客户端开发人员正确集成工具确认功能。