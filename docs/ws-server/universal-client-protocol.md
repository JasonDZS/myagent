# MyAgent WebSocket 通信协议

## 概述

本文档描述 MyAgent WebSocket 服务器的客户端-服务器通信协议。该协议基于事件驱动架构，支持实时双向通信、会话管理、用户确认机制和客户端状态管理。

## 协议特性

### 🚀 核心特性
- **事件驱动架构**: 基于统一的事件系统进行通信
- **会话管理**: 支持会话创建、状态导出和恢复
- **用户确认**: 危险操作前的用户确认流程
- **客户端状态管理**: 支持离线状态保存和恢复
- **流式回答**: 实时显示Agent思考和回答过程

## 消息格式

### 基础事件结构

```typescript
interface WebSocketMessage {
  event: string;               // 事件类型
  timestamp: string;           // ISO时间戳
  session_id?: string;         // 会话ID (非系统事件必需)
  step_id?: string;           // 步骤ID (用于请求响应关联)
  content?: string | object;   // 消息内容
  metadata?: object;           // 元数据
}
```

## 事件类型

### 用户事件 (客户端发送)
```javascript
user.create_session        // 创建会话
user.message              // 发送消息  
user.response             // 确认响应
user.cancel               // 取消执行
user.request_state        // 请求导出状态
user.reconnect_with_state // 使用状态重连
```

### Agent事件 (服务器发送)
```javascript
agent.session_created  // 会话创建成功
agent.thinking         // 思考状态
agent.tool_call        // 工具调用
agent.tool_result      // 工具结果
agent.user_confirm     // 请求确认
agent.partial_answer   // 流式回答
agent.final_answer     // 最终回答
agent.state_exported   // 状态导出完成
agent.state_restored   // 状态恢复完成
agent.error           // 执行错误
```

### 系统事件 (服务器发送)
```javascript
system.connected    // 连接确认
system.heartbeat    // 心跳检测
system.error        // 系统错误
```

## 基础通信流程

### 1. 连接建立

```javascript
const ws = new WebSocket('ws://localhost:8080');

ws.onopen = () => {
    console.log('Connected to server');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
};
```

### 2. 创建会话

```javascript
// 发送创建会话请求
ws.send(JSON.stringify({
    event: 'user.create_session',
    timestamp: new Date().toISOString(),
    content: 'create_session'
}));

// 处理会话创建成功响应
function handleMessage(data) {
    if (data.event === 'agent.session_created') {
        const sessionId = data.session_id;
        console.log('Session created:', sessionId);
    }
}
```

### 3. 发送消息

```javascript
ws.send(JSON.stringify({
    event: 'user.message',
    session_id: sessionId,
    content: '你好！',
    timestamp: new Date().toISOString()
}));
```

### 4. 处理用户确认

```javascript
function handleMessage(data) {
    if (data.event === 'agent.user_confirm') {
        const shouldConfirm = confirm(`确认执行: ${data.metadata?.tool_description}?`);
        
        ws.send(JSON.stringify({
            event: 'user.response',
            session_id: data.session_id,
            step_id: data.step_id,
            content: { confirmed: shouldConfirm },
            timestamp: new Date().toISOString()
        }));
    }
}

## 完整示例

### JavaScript 客户端

```javascript
class SimpleWebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.sessionId = null;
    }

    connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('Connected');
                resolve();
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
            
            this.ws.onerror = reject;
        });
    }

    async createSession() {
        this.send({
            event: 'user.create_session',
            timestamp: new Date().toISOString(),
            content: 'create_session'
        });
    }

    sendMessage(content) {
        this.send({
            event: 'user.message',
            session_id: this.sessionId,
            content: content,
            timestamp: new Date().toISOString()
        });
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    handleMessage(data) {
        switch (data.event) {
            case 'agent.session_created':
                this.sessionId = data.session_id;
                console.log('Session created:', this.sessionId);
                break;
            case 'agent.thinking':
                console.log('Agent thinking:', data.content);
                break;
            case 'agent.final_answer':
                console.log('Agent answer:', data.content);
                break;
            case 'agent.user_confirm':
                this.handleUserConfirm(data);
                break;
            case 'system.error':
            case 'agent.error':
                console.error('Error:', data.content);
                break;
        }
    }

    handleUserConfirm(data) {
        const confirmed = confirm(`确认执行工具: ${data.metadata?.tool_description}?`);
        this.send({
            event: 'user.response',
            session_id: data.session_id,
            step_id: data.step_id,
            content: { confirmed },
            timestamp: new Date().toISOString()
        });
    }
}

// 使用示例
async function demo() {
    const client = new SimpleWebSocketClient('ws://localhost:8080');
    await client.connect();
    await client.createSession();
    
    // 等待一秒确保会话创建完成
    setTimeout(() => {
        client.sendMessage('Hello, what can you help me with?');
    }, 1000);
}
```

## 客户端状态管理

MyAgent 支持客户端状态管理，允许在客户端保存会话状态，实现长期离线后的状态恢复。详细信息请参考 [客户端状态管理文档](./client-state-management.md)。

### 状态导出

```javascript
// 请求导出当前会话状态
ws.send(JSON.stringify({
    event: 'user.request_state',
    session_id: sessionId,
    timestamp: new Date().toISOString()
}));

// 处理状态导出成功响应
function handleMessage(data) {
    if (data.event === 'agent.state_exported') {
        const signedState = data.metadata.signed_state;
        // 保存状态到本地存储
        localStorage.setItem(`session_${sessionId}`, JSON.stringify(signedState));
    }
}
```

### 状态恢复

```javascript
// 从本地存储加载状态
const savedState = JSON.parse(localStorage.getItem(`session_${oldSessionId}`));

// 使用状态重新连接
ws.send(JSON.stringify({
    event: 'user.reconnect_with_state',
    signed_state: savedState,
    timestamp: new Date().toISOString()
}));

// 处理状态恢复成功响应
function handleMessage(data) {
    if (data.event === 'agent.state_restored') {
        console.log('Session restored:', data.session_id);
        // 继续使用恢复的会话
    }
}
```

---

更多详细信息和高级用法，请参考相关文档：
- [快速开始](./quick-start.md)
- [用户确认机制](./user-confirmation.md)
- [React 集成](./react-integration.md)