# MyAgent WebSocket 前端对接文档

## 概述

本文档提供了与 MyAgent WebSocket 服务器进行前端集成的完整指南，包括连接管理、事件处理、错误处理和最佳实践。

---

## 1. 快速开始

### 1.1 基本连接

```javascript
// 基本连接示例
const ws = new WebSocket('ws://localhost:8080');

ws.onopen = function(event) {
    console.log('✅ WebSocket 连接已建立');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('📨 收到消息:', data);
};

ws.onerror = function(error) {
    console.error('❌ WebSocket 错误:', error);
};

ws.onclose = function(event) {
    console.log('🔌 WebSocket 连接已关闭');
};
```

### 1.2 完整的客户端示例

```javascript
class MyAgentClient {
    constructor(url = 'ws://localhost:8080') {
        this.url = url;
        this.ws = null;
        this.sessionId = null;
        this.connectionId = null;
        
        // 事件回调
        this.onConnected = null;
        this.onSessionCreated = null;
        this.onThinking = null;
        this.onPartialAnswer = null;
        this.onFinalAnswer = null;
        this.onToolCall = null;
        this.onToolResult = null;
        this.onError = null;
    }

    async connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('🔗 WebSocket 连接成功');
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                reject(error);
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket 连接关闭:', event.code, event.reason);
            };
        });
    }
    
    handleMessage(data) {
        const { event, session_id, content, metadata } = data;
        
        switch (event) {
            case 'system.connected':
                this.connectionId = metadata?.connection_id;
                console.log('✅ 系统连接确认');
                this.onConnected?.(data);
                break;
                
            case 'agent.session_created':
                this.sessionId = session_id;
                console.log('🚀 会话创建成功:', session_id);
                this.onSessionCreated?.(data);
                break;
                
            case 'agent.thinking':
                console.log('💭 Agent 思考中:', content);
                this.onThinking?.(data);
                break;
                
            case 'agent.partial_answer':
                console.log('📄 部分回答:', content);
                this.onPartialAnswer?.(data);
                break;
                
            case 'agent.final_answer':
                console.log('🎯 最终回答:', content);
                this.onFinalAnswer?.(data);
                break;
                
            case 'agent.tool_call':
                console.log('🔧 工具调用:', metadata);
                this.onToolCall?.(data);
                break;
                
            case 'agent.tool_result':
                console.log('📊 工具结果:', content);
                this.onToolResult?.(data);
                break;
                
            case 'agent.error':
            case 'system.error':
                console.error('❌ 错误:', content);
                this.onError?.(data);
                break;
                
            default:
                console.log('📨 其他事件:', data);
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
            throw new Error('会话未创建，请先调用 createSession()');
        }
        
        const message = {
            session_id: this.sessionId,
            event: 'user.message',
            timestamp: new Date().toISOString(),
            content: content
        };
        this.send(message);
    }
    
    cancelExecution() {
        if (!this.sessionId) return;
        
        const message = {
            session_id: this.sessionId,
            event: 'user.cancel',
            timestamp: new Date().toISOString(),
            content: 'cancel'
        };
        this.send(message);
    }
    
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket 未连接');
        }
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}
```

---

## 2. 事件协议详解

### 2.1 消息格式

所有 WebSocket 消息都采用 JSON 格式：

```typescript
interface WebSocketMessage {
    event: string;           // 事件类型
    timestamp: string;       // ISO 格式时间戳
    session_id?: string;     // 会话 ID（可选）
    connection_id?: string;  // 连接 ID（可选）
    step_id?: string;        // 步骤 ID（可选）
    content?: string | object; // 消息内容
    metadata?: object;       // 元数据
}
```

### 2.2 用户事件 (发送给服务器)

#### `user.create_session` - 创建会话
```javascript
{
    "event": "user.create_session",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "create_session"
}
```

#### `user.message` - 发送消息
```javascript
{
    "session_id": "session_123",
    "event": "user.message", 
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "北京今天天气怎么样？"
}
```

#### `user.cancel` - 取消执行
```javascript
{
    "session_id": "session_123",
    "event": "user.cancel",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "cancel"
}
```

### 2.3 Agent 事件 (服务器发送)

#### `agent.session_created` - 会话创建成功
```javascript
{
    "event": "agent.session_created",
    "session_id": "session_123", 
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "会话创建成功",
    "metadata": {
        "agent_name": "weather-assistant",
        "connection_id": "conn_456"
    }
}
```

#### `agent.thinking` - Agent 思考状态
```javascript
{
    "event": "agent.thinking",
    "session_id": "session_123",
    "timestamp": "2024-01-01T12:00:00.000Z", 
    "content": "正在分析您的问题...",
    "metadata": {
        "step": 1,
        "streaming": true
    }
}
```

#### `agent.tool_call` - 工具调用开始
```javascript
{
    "event": "agent.tool_call",
    "session_id": "session_123",
    "step_id": "step_1_weather_api",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "调用工具: weather_api",
    "metadata": {
        "tool": "weather_api",
        "args": {"city": "北京"},
        "status": "running"
    }
}
```

#### `agent.tool_result` - 工具调用结果
```javascript
{
    "event": "agent.tool_result", 
    "session_id": "session_123",
    "step_id": "step_1_weather_api",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "北京的天气：25°C，晴朗，湿度45%",
    "metadata": {
        "tool": "weather_api",
        "status": "success"
    }
}
```

#### `agent.partial_answer` - 流式回答片段
```javascript
{
    "event": "agent.partial_answer",
    "session_id": "session_123", 
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "根据最新的天气数据显示",
    "metadata": {
        "is_streaming": true,
        "word_count": 25,
        "is_final": false
    }
}
```

#### `agent.final_answer` - 最终回答
```javascript
{
    "event": "agent.final_answer",
    "session_id": "session_123",
    "timestamp": "2024-01-01T12:00:00.000Z", 
    "content": "北京今天的天气是25°C，晴朗，湿度45%。适合外出活动。"
}
```

### 2.4 系统事件

#### `system.connected` - 连接确认
```javascript
{
    "event": "system.connected",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "Connected to MyAgent WebSocket Server", 
    "metadata": {
        "connection_id": "conn_456"
    }
}
```

#### `system.heartbeat` - 心跳检测
```javascript
{
    "event": "system.heartbeat",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "metadata": {
        "active_sessions": 3,
        "uptime": 3600
    }
}
```

#### `system.error` - 系统错误
```javascript
{
    "event": "system.error",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "content": "Invalid JSON: Expecting property name enclosed in double quotes"
}
```

---

## 3. React 集成示例

### 3.1 React Hook

```tsx
import { useState, useEffect, useRef, useCallback } from 'react';

interface UseMyAgentOptions {
    url?: string;
    autoConnect?: boolean;
}

interface AgentMessage {
    id: string;
    type: 'user' | 'agent' | 'system';
    content: string;
    timestamp: Date;
    metadata?: any;
}

export function useMyAgent(options: UseMyAgentOptions = {}) {
    const { url = 'ws://localhost:8080', autoConnect = true } = options;
    
    const [connected, setConnected] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [messages, setMessages] = useState<AgentMessage[]>([]);
    const [thinking, setThinking] = useState(false);
    const [streaming, setStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    const wsRef = useRef<WebSocket | null>(null);
    const streamingContentRef = useRef<string>('');
    
    const connect = useCallback(async () => {
        try {
            const ws = new WebSocket(url);
            wsRef.current = ws;
            
            ws.onopen = () => {
                setConnected(true);
                setError(null);
                console.log('WebSocket 连接成功');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onerror = (error) => {
                setError('WebSocket 连接错误');
                console.error('WebSocket 错误:', error);
            };
            
            ws.onclose = () => {
                setConnected(false);
                setSessionId(null);
                console.log('WebSocket 连接关闭');
            };
            
        } catch (err) {
            setError('连接失败');
        }
    }, [url]);
    
    const handleMessage = (data: any) => {
        const { event, session_id, content, metadata } = data;
        
        switch (event) {
            case 'system.connected':
                // 自动创建会话
                createSession();
                break;
                
            case 'agent.session_created':
                setSessionId(session_id);
                break;
                
            case 'agent.thinking':
                setThinking(true);
                addMessage({
                    type: 'system',
                    content: content || 'Agent 正在思考...',
                    metadata
                });
                break;
                
            case 'agent.partial_answer':
                if (!streaming) {
                    setStreaming(true);
                    streamingContentRef.current = '';
                }
                
                if (content) {
                    streamingContentRef.current += content;
                    updateLastStreamingMessage(streamingContentRef.current);
                }
                
                if (metadata?.is_final) {
                    setStreaming(false);
                    setThinking(false);
                }
                break;
                
            case 'agent.final_answer':
                setThinking(false);
                setStreaming(false);
                addMessage({
                    type: 'agent',
                    content: content || '',
                    metadata
                });
                break;
                
            case 'agent.tool_call':
                addMessage({
                    type: 'system',
                    content: `🔧 ${content}`,
                    metadata
                });
                break;
                
            case 'agent.tool_result':
                addMessage({
                    type: 'system', 
                    content: `📊 ${content}`,
                    metadata
                });
                break;
                
            case 'agent.error':
            case 'system.error':
                setError(content || '未知错误');
                setThinking(false);
                setStreaming(false);
                break;
        }
    };
    
    const addMessage = (msg: Omit<AgentMessage, 'id' | 'timestamp'>) => {
        const newMessage: AgentMessage = {
            ...msg,
            id: Date.now().toString(),
            timestamp: new Date()
        };
        setMessages(prev => [...prev, newMessage]);
    };
    
    const updateLastStreamingMessage = (content: string) => {
        setMessages(prev => {
            const updated = [...prev];
            const lastMsg = updated[updated.length - 1];
            
            if (lastMsg && lastMsg.type === 'agent' && lastMsg.metadata?.streaming) {
                lastMsg.content = content;
            } else {
                // 添加新的流式消息
                updated.push({
                    id: 'streaming',
                    type: 'agent',
                    content,
                    timestamp: new Date(),
                    metadata: { streaming: true }
                });
            }
            return updated;
        });
    };
    
    const createSession = () => {
        const message = {
            event: 'user.create_session',
            timestamp: new Date().toISOString(),
            content: 'create_session'
        };
        send(message);
    };
    
    const sendMessage = (content: string) => {
        if (!sessionId) {
            setError('会话未创建');
            return;
        }
        
        // 添加用户消息到列表
        addMessage({
            type: 'user',
            content
        });
        
        const message = {
            session_id: sessionId,
            event: 'user.message',
            timestamp: new Date().toISOString(),
            content
        };
        send(message);
        
        setThinking(true);
        setError(null);
    };
    
    const cancelExecution = () => {
        if (!sessionId) return;
        
        const message = {
            session_id: sessionId,
            event: 'user.cancel',
            timestamp: new Date().toISOString(),
            content: 'cancel'
        };
        send(message);
    };
    
    const send = (message: any) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
        } else {
            setError('WebSocket 未连接');
        }
    };
    
    const disconnect = () => {
        if (wsRef.current) {
            wsRef.current.close();
        }
    };
    
    useEffect(() => {
        if (autoConnect) {
            connect();
        }
        
        return () => {
            disconnect();
        };
    }, [connect, autoConnect]);
    
    return {
        connected,
        sessionId,
        messages,
        thinking,
        streaming,
        error,
        connect,
        disconnect,
        sendMessage,
        cancelExecution
    };
}
```

### 3.2 Chat 组件示例

```tsx
import React, { useState } from 'react';
import { useMyAgent } from './hooks/useMyAgent';

export function ChatInterface() {
    const [input, setInput] = useState('');
    const { 
        connected, 
        messages, 
        thinking, 
        streaming, 
        error, 
        sendMessage, 
        cancelExecution 
    } = useMyAgent();
    
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            sendMessage(input.trim());
            setInput('');
        }
    };
    
    return (
        <div className="chat-container">
            {/* 连接状态 */}
            <div className="status-bar">
                <span className={`status ${connected ? 'connected' : 'disconnected'}`}>
                    {connected ? '🟢 已连接' : '🔴 未连接'}
                </span>
                {error && <span className="error">❌ {error}</span>}
            </div>
            
            {/* 消息列表 */}
            <div className="messages">
                {messages.map((msg) => (
                    <div key={msg.id} className={`message ${msg.type}`}>
                        <div className="message-content">
                            {msg.content}
                            {msg.metadata?.streaming && streaming && (
                                <span className="streaming-indicator">▊</span>
                            )}
                        </div>
                        <div className="message-time">
                            {msg.timestamp.toLocaleTimeString()}
                        </div>
                    </div>
                ))}
                
                {thinking && !streaming && (
                    <div className="message system thinking">
                        <div className="message-content">
                            💭 Agent 正在思考...
                            <div className="thinking-dots">
                                <span></span><span></span><span></span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
            
            {/* 输入区域 */}
            <form onSubmit={handleSubmit} className="input-form">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="输入您的问题..."
                    disabled={!connected || thinking}
                    className="message-input"
                />
                <button 
                    type="submit" 
                    disabled={!connected || !input.trim() || thinking}
                    className="send-button"
                >
                    发送
                </button>
                {thinking && (
                    <button 
                        type="button"
                        onClick={cancelExecution}
                        className="cancel-button"
                    >
                        取消
                    </button>
                )}
            </form>
        </div>
    );
}
```

### 3.3 样式示例 (CSS)

```css
.chat-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 800px;
    margin: 0 auto;
    border: 1px solid #ddd;
    border-radius: 8px;
    overflow: hidden;
}

.status-bar {
    padding: 8px 16px;
    background-color: #f5f5f5;
    border-bottom: 1px solid #ddd;
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 12px;
}

.status.connected {
    color: #22c55e;
}

.status.disconnected {
    color: #ef4444;
}

.error {
    color: #ef4444;
    font-weight: 500;
}

.messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.message {
    max-width: 80%;
    padding: 12px 16px;
    border-radius: 12px;
    position: relative;
}

.message.user {
    align-self: flex-end;
    background-color: #3b82f6;
    color: white;
}

.message.agent {
    align-self: flex-start;
    background-color: #f1f5f9;
    color: #334155;
}

.message.system {
    align-self: center;
    background-color: #fef3c7;
    color: #92400e;
    font-size: 14px;
    max-width: 90%;
}

.message-content {
    margin-bottom: 4px;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.message-time {
    font-size: 11px;
    opacity: 0.7;
}

.streaming-indicator {
    display: inline-block;
    animation: blink 1s infinite;
    margin-left: 2px;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

.thinking {
    font-style: italic;
}

.thinking-dots {
    display: inline-flex;
    gap: 2px;
    margin-left: 4px;
}

.thinking-dots span {
    width: 4px;
    height: 4px;
    background-color: currentColor;
    border-radius: 50%;
    animation: thinking 1.4s ease-in-out infinite both;
}

.thinking-dots span:nth-child(1) { animation-delay: -0.32s; }
.thinking-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes thinking {
    0%, 80%, 100% {
        transform: scale(0);
        opacity: 0.5;
    }
    40% {
        transform: scale(1);
        opacity: 1;
    }
}

.input-form {
    padding: 16px;
    border-top: 1px solid #ddd;
    display: flex;
    gap: 8px;
}

.message-input {
    flex: 1;
    padding: 10px 16px;
    border: 1px solid #ddd;
    border-radius: 20px;
    outline: none;
    font-size: 14px;
}

.message-input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.send-button, .cancel-button {
    padding: 10px 20px;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: background-color 0.2s;
}

.send-button {
    background-color: #3b82f6;
    color: white;
}

.send-button:hover:not(:disabled) {
    background-color: #2563eb;
}

.send-button:disabled {
    background-color: #94a3b8;
    cursor: not-allowed;
}

.cancel-button {
    background-color: #ef4444;
    color: white;
}

.cancel-button:hover {
    background-color: #dc2626;
}
```

---

## 4. Vue.js 集成示例

### 4.1 Vue Composition API

```vue
<template>
  <div class="chat-container">
    <!-- 连接状态 -->
    <div class="status-bar">
      <span :class="`status ${connected ? 'connected' : 'disconnected'}`">
        {{ connected ? '🟢 已连接' : '🔴 未连接' }}
      </span>
      <span v-if="error" class="error">❌ {{ error }}</span>
    </div>

    <!-- 消息列表 -->
    <div class="messages" ref="messagesContainer">
      <div 
        v-for="msg in messages" 
        :key="msg.id" 
        :class="`message ${msg.type}`"
      >
        <div class="message-content">
          {{ msg.content }}
          <span v-if="msg.metadata?.streaming && streaming" class="streaming-indicator">▊</span>
        </div>
        <div class="message-time">
          {{ formatTime(msg.timestamp) }}
        </div>
      </div>

      <div v-if="thinking && !streaming" class="message system thinking">
        <div class="message-content">
          💭 Agent 正在思考...
          <div class="thinking-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <form @submit.prevent="handleSubmit" class="input-form">
      <input
        v-model="input"
        type="text"
        placeholder="输入您的问题..."
        :disabled="!connected || thinking"
        class="message-input"
      />
      <button 
        type="submit" 
        :disabled="!connected || !input.trim() || thinking"
        class="send-button"
      >
        发送
      </button>
      <button 
        v-if="thinking"
        type="button"
        @click="cancelExecution"
        class="cancel-button"
      >
        取消
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue';

// Props
const props = defineProps({
  url: {
    type: String,
    default: 'ws://localhost:8080'
  }
});

// Reactive state
const ws = ref(null);
const connected = ref(false);
const sessionId = ref(null);
const messages = ref([]);
const thinking = ref(false);
const streaming = ref(false);
const error = ref(null);
const input = ref('');
const messagesContainer = ref(null);
const streamingContent = ref('');

// Connect to WebSocket
const connect = async () => {
  try {
    ws.value = new WebSocket(props.url);
    
    ws.value.onopen = () => {
      connected.value = true;
      error.value = null;
      console.log('WebSocket 连接成功');
    };
    
    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };
    
    ws.value.onerror = (err) => {
      error.value = 'WebSocket 连接错误';
      console.error('WebSocket 错误:', err);
    };
    
    ws.value.onclose = () => {
      connected.value = false;
      sessionId.value = null;
      console.log('WebSocket 连接关闭');
    };
    
  } catch (err) {
    error.value = '连接失败';
  }
};

// Handle incoming messages
const handleMessage = (data) => {
  const { event, session_id, content, metadata } = data;
  
  switch (event) {
    case 'system.connected':
      createSession();
      break;
      
    case 'agent.session_created':
      sessionId.value = session_id;
      break;
      
    case 'agent.thinking':
      thinking.value = true;
      addMessage({
        type: 'system',
        content: content || 'Agent 正在思考...',
        metadata
      });
      break;
      
    case 'agent.partial_answer':
      if (!streaming.value) {
        streaming.value = true;
        streamingContent.value = '';
      }
      
      if (content) {
        streamingContent.value += content;
        updateLastStreamingMessage(streamingContent.value);
      }
      
      if (metadata?.is_final) {
        streaming.value = false;
        thinking.value = false;
      }
      break;
      
    case 'agent.final_answer':
      thinking.value = false;
      streaming.value = false;
      addMessage({
        type: 'agent',
        content: content || '',
        metadata
      });
      break;
      
    case 'agent.tool_call':
      addMessage({
        type: 'system',
        content: `🔧 ${content}`,
        metadata
      });
      break;
      
    case 'agent.tool_result':
      addMessage({
        type: 'system', 
        content: `📊 ${content}`,
        metadata
      });
      break;
      
    case 'agent.error':
    case 'system.error':
      error.value = content || '未知错误';
      thinking.value = false;
      streaming.value = false;
      break;
  }
};

// Add message to list
const addMessage = (msg) => {
  const newMessage = {
    ...msg,
    id: Date.now().toString(),
    timestamp: new Date()
  };
  messages.value.push(newMessage);
  scrollToBottom();
};

// Update streaming message
const updateLastStreamingMessage = (content) => {
  const lastMsg = messages.value[messages.value.length - 1];
  
  if (lastMsg && lastMsg.type === 'agent' && lastMsg.metadata?.streaming) {
    lastMsg.content = content;
  } else {
    // Add new streaming message
    messages.value.push({
      id: 'streaming',
      type: 'agent',
      content,
      timestamp: new Date(),
      metadata: { streaming: true }
    });
  }
  scrollToBottom();
};

// Create session
const createSession = () => {
  const message = {
    event: 'user.create_session',
    timestamp: new Date().toISOString(),
    content: 'create_session'
  };
  send(message);
};

// Send message
const sendMessage = (content) => {
  if (!sessionId.value) {
    error.value = '会话未创建';
    return;
  }
  
  addMessage({
    type: 'user',
    content
  });
  
  const message = {
    session_id: sessionId.value,
    event: 'user.message',
    timestamp: new Date().toISOString(),
    content
  };
  send(message);
  
  thinking.value = true;
  error.value = null;
};

// Cancel execution
const cancelExecution = () => {
  if (!sessionId.value) return;
  
  const message = {
    session_id: sessionId.value,
    event: 'user.cancel',
    timestamp: new Date().toISOString(),
    content: 'cancel'
  };
  send(message);
};

// Send WebSocket message
const send = (message) => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify(message));
  } else {
    error.value = 'WebSocket 未连接';
  }
};

// Handle form submission
const handleSubmit = () => {
  if (input.value.trim()) {
    sendMessage(input.value.trim());
    input.value = '';
  }
};

// Scroll to bottom
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

// Format time
const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString();
};

// Lifecycle hooks
onMounted(() => {
  connect();
});

onUnmounted(() => {
  if (ws.value) {
    ws.value.close();
  }
});

// Watch for new messages to scroll
watch(messages, scrollToBottom, { deep: true });
</script>

<style scoped>
/* 样式与 React 版本相同 */
</style>
```

---

## 5. 错误处理与重连机制

### 5.1 错误处理

```javascript
class RobustWebSocketClient {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            maxRetries: 5,
            retryDelay: 1000,
            maxRetryDelay: 30000,
            heartbeatInterval: 30000,
            ...options
        };
        
        this.ws = null;
        this.reconnectCount = 0;
        this.heartbeatTimer = null;
        this.isManualClose = false;
        
        // 事件回调
        this.onMessage = null;
        this.onConnect = null;
        this.onDisconnect = null;
        this.onError = null;
    }
    
    async connect() {
        this.isManualClose = false;
        
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.url);
                
                const timeout = setTimeout(() => {
                    this.ws.close();
                    reject(new Error('连接超时'));
                }, 10000);
                
                this.ws.onopen = () => {
                    clearTimeout(timeout);
                    this.reconnectCount = 0;
                    this.startHeartbeat();
                    console.log('WebSocket 连接成功');
                    this.onConnect?.();
                    resolve();
                };
                
                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    } catch (err) {
                        console.error('消息解析错误:', err);
                    }
                };
                
                this.ws.onerror = (error) => {
                    clearTimeout(timeout);
                    console.error('WebSocket 错误:', error);
                    this.onError?.(error);
                };
                
                this.ws.onclose = (event) => {
                    clearTimeout(timeout);
                    this.stopHeartbeat();
                    
                    console.log('WebSocket 连接关闭:', event.code, event.reason);
                    this.onDisconnect?.(event);
                    
                    // 自动重连（除非是手动关闭）
                    if (!this.isManualClose) {
                        this.scheduleReconnect();
                    }
                };
                
            } catch (err) {
                reject(err);
            }
        });
    }
    
    handleMessage(data) {
        // 处理心跳响应
        if (data.event === 'system.heartbeat') {
            console.log('收到心跳响应');
            return;
        }
        
        this.onMessage?.(data);
    }
    
    scheduleReconnect() {
        if (this.reconnectCount >= this.options.maxRetries) {
            console.error('重连次数超过限制，停止重连');
            return;
        }
        
        const delay = Math.min(
            this.options.retryDelay * Math.pow(2, this.reconnectCount),
            this.options.maxRetryDelay
        );
        
        console.log(`${delay}ms 后尝试重连 (第 ${this.reconnectCount + 1} 次)`);
        
        setTimeout(() => {
            this.reconnectCount++;
            this.connect().catch(() => {
                // 重连失败，继续下次尝试
            });
        }, delay);
    }
    
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected()) {
                this.send({
                    event: 'system.ping',
                    timestamp: new Date().toISOString()
                });
            }
        }, this.options.heartbeatInterval);
    }
    
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    send(data) {
        if (this.isConnected()) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }
    
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
    
    close() {
        this.isManualClose = true;
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close();
        }
    }
}
```

### 5.2 连接状态管理

```javascript
class ConnectionManager {
    constructor() {
        this.status = 'disconnected'; // disconnected, connecting, connected, reconnecting
        this.quality = 'unknown'; // excellent, good, poor, unstable
        this.latency = 0;
        this.lastPingTime = null;
        
        this.listeners = new Map();
    }
    
    setStatus(status) {
        const oldStatus = this.status;
        this.status = status;
        
        if (oldStatus !== status) {
            this.emit('statusChange', { oldStatus, newStatus: status });
        }
    }
    
    updateLatency(latency) {
        this.latency = latency;
        
        // 根据延迟判断连接质量
        if (latency < 100) {
            this.quality = 'excellent';
        } else if (latency < 300) {
            this.quality = 'good';
        } else if (latency < 1000) {
            this.quality = 'poor';
        } else {
            this.quality = 'unstable';
        }
        
        this.emit('qualityChange', { latency, quality: this.quality });
    }
    
    ping() {
        this.lastPingTime = Date.now();
        return {
            event: 'system.ping',
            timestamp: new Date().toISOString(),
            clientTime: this.lastPingTime
        };
    }
    
    handlePong(serverTime) {
        if (this.lastPingTime) {
            const latency = Date.now() - this.lastPingTime;
            this.updateLatency(latency);
        }
    }
    
    on(event, listener) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(listener);
    }
    
    off(event, listener) {
        if (this.listeners.has(event)) {
            const listeners = this.listeners.get(event);
            const index = listeners.indexOf(listener);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }
    
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(listener => {
                try {
                    listener(data);
                } catch (err) {
                    console.error('事件监听器错误:', err);
                }
            });
        }
    }
}
```

---

## 6. 最佳实践

### 6.1 性能优化

```javascript
// 消息缓存和批处理
class MessageBuffer {
    constructor(options = {}) {
        this.buffer = [];
        this.maxSize = options.maxSize || 100;
        this.flushInterval = options.flushInterval || 16; // 60 FPS
        this.timer = null;
        this.onFlush = options.onFlush || (() => {});
    }
    
    add(message) {
        this.buffer.push({
            ...message,
            timestamp: Date.now()
        });
        
        if (this.buffer.length >= this.maxSize) {
            this.flush();
        } else if (!this.timer) {
            this.timer = setTimeout(() => {
                this.flush();
            }, this.flushInterval);
        }
    }
    
    flush() {
        if (this.buffer.length > 0) {
            this.onFlush(this.buffer.splice(0));
        }
        
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
    }
}

// 使用示例
const messageBuffer = new MessageBuffer({
    maxSize: 10,
    flushInterval: 50,
    onFlush: (messages) => {
        // 批量更新 UI
        setMessages(prev => [...prev, ...messages]);
    }
});
```

### 6.2 内存管理

```javascript
// 消息列表管理
class MessageManager {
    constructor(maxMessages = 1000) {
        this.messages = [];
        this.maxMessages = maxMessages;
    }
    
    addMessage(message) {
        this.messages.push({
            ...message,
            id: this.generateId(),
            timestamp: new Date()
        });
        
        // 防止内存泄漏
        if (this.messages.length > this.maxMessages) {
            this.messages.splice(0, this.messages.length - this.maxMessages);
        }
    }
    
    getMessages() {
        return this.messages;
    }
    
    clear() {
        this.messages = [];
    }
    
    generateId() {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}
```

### 6.3 安全考虑

```javascript
// 消息验证
class MessageValidator {
    static validate(data) {
        // 基本结构验证
        if (!data || typeof data !== 'object') {
            throw new Error('消息格式无效');
        }
        
        if (!data.event || typeof data.event !== 'string') {
            throw new Error('事件类型无效');
        }
        
        // 内容长度限制
        if (data.content && typeof data.content === 'string') {
            if (data.content.length > 50000) {
                throw new Error('消息内容过长');
            }
        }
        
        // XSS 防护
        if (typeof data.content === 'string') {
            data.content = MessageValidator.sanitizeContent(data.content);
        }
        
        return data;
    }
    
    static sanitizeContent(content) {
        // 简单的 XSS 防护（实际项目中建议使用专门的库）
        return content
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;');
    }
}
```

### 6.4 错误边界

```tsx
// React Error Boundary
class WebSocketErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }
    
    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }
    
    componentDidCatch(error, errorInfo) {
        console.error('WebSocket 组件错误:', error, errorInfo);
        
        // 发送错误报告到监控系统
        if (typeof window !== 'undefined' && window.analytics) {
            window.analytics.track('WebSocket Error', {
                error: error.message,
                stack: error.stack,
                componentStack: errorInfo.componentStack
            });
        }
    }
    
    render() {
        if (this.state.hasError) {
            return (
                <div className="error-boundary">
                    <h2>连接出现问题</h2>
                    <p>WebSocket 连接遇到错误，请刷新页面重试。</p>
                    <button onClick={() => window.location.reload()}>
                        刷新页面
                    </button>
                </div>
            );
        }
        
        return this.props.children;
    }
}
```

---

## 7. 调试工具

### 7.1 WebSocket 调试器

```javascript
class WebSocketDebugger {
    constructor(ws) {
        this.ws = ws;
        this.logs = [];
        this.enabled = process.env.NODE_ENV === 'development';
    }
    
    log(type, data, direction = 'in') {
        if (!this.enabled) return;
        
        const logEntry = {
            timestamp: new Date().toISOString(),
            type,
            direction, // 'in' | 'out'
            data: JSON.parse(JSON.stringify(data)),
            readyState: this.ws?.readyState
        };
        
        this.logs.push(logEntry);
        
        // 控制台输出
        const emoji = direction === 'out' ? '📤' : '📥';
        const style = direction === 'out' ? 'color: #10b981' : 'color: #3b82f6';
        
        console.groupCollapsed(`${emoji} ${type} - ${logEntry.timestamp}`);
        console.log('%c数据:', style, data);
        console.log('连接状态:', this.getReadyStateText());
        console.groupEnd();
    }
    
    getReadyStateText() {
        const states = {
            0: 'CONNECTING',
            1: 'OPEN',
            2: 'CLOSING', 
            3: 'CLOSED'
        };
        return states[this.ws?.readyState] || 'UNKNOWN';
    }
    
    exportLogs() {
        return {
            logs: this.logs,
            summary: {
                total: this.logs.length,
                byType: this.logs.reduce((acc, log) => {
                    acc[log.type] = (acc[log.type] || 0) + 1;
                    return acc;
                }, {}),
                byDirection: this.logs.reduce((acc, log) => {
                    acc[log.direction] = (acc[log.direction] || 0) + 1;
                    return acc;
                }, {})
            }
        };
    }
    
    clear() {
        this.logs = [];
        console.clear();
    }
}
```

### 7.2 性能监控

```javascript
class WebSocketPerformanceMonitor {
    constructor() {
        this.metrics = {
            messageCount: 0,
            bytesReceived: 0,
            bytesSent: 0,
            averageLatency: 0,
            connectionUptime: 0,
            reconnectCount: 0
        };
        
        this.startTime = null;
        this.latencyHistory = [];
    }
    
    recordMessage(data, direction) {
        this.metrics.messageCount++;
        
        const bytes = new Blob([JSON.stringify(data)]).size;
        if (direction === 'in') {
            this.metrics.bytesReceived += bytes;
        } else {
            this.metrics.bytesSent += bytes;
        }
    }
    
    recordLatency(latency) {
        this.latencyHistory.push(latency);
        
        // 只保留最近 100 次的延迟记录
        if (this.latencyHistory.length > 100) {
            this.latencyHistory.shift();
        }
        
        this.metrics.averageLatency = 
            this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length;
    }
    
    startTimer() {
        this.startTime = Date.now();
    }
    
    updateUptime() {
        if (this.startTime) {
            this.metrics.connectionUptime = Date.now() - this.startTime;
        }
    }
    
    recordReconnect() {
        this.metrics.reconnectCount++;
    }
    
    getReport() {
        this.updateUptime();
        
        return {
            ...this.metrics,
            uptimeFormatted: this.formatDuration(this.metrics.connectionUptime),
            throughput: {
                messagesPerMinute: this.metrics.messageCount / (this.metrics.connectionUptime / 60000),
                bytesPerSecond: (this.metrics.bytesReceived + this.metrics.bytesSent) / (this.metrics.connectionUptime / 1000)
            }
        };
    }
    
    formatDuration(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}:${minutes % 60}:${seconds % 60}`;
        } else if (minutes > 0) {
            return `${minutes}:${seconds % 60}`;
        } else {
            return `${seconds}s`;
        }
    }
}
```

---

## 8. TypeScript 类型定义

```typescript
// 事件类型定义
export type WebSocketEventType = 
  // 用户事件
  | 'user.create_session'
  | 'user.message' 
  | 'user.response'
  | 'user.cancel'
  | 'user.reconnect'
  // Agent 事件
  | 'agent.session_created'
  | 'agent.thinking'
  | 'agent.tool_call'
  | 'agent.tool_result' 
  | 'agent.partial_answer'
  | 'agent.final_answer'
  | 'agent.user_confirm'
  | 'agent.error'
  | 'agent.timeout'
  | 'agent.interrupted'
  | 'agent.session_end'
  // 系统事件
  | 'system.connected'
  | 'system.heartbeat'
  | 'system.error';

export interface WebSocketMessage {
  event: WebSocketEventType;
  timestamp: string;
  session_id?: string;
  connection_id?: string;
  step_id?: string;
  content?: string | object;
  metadata?: Record<string, any>;
}

export interface AgentMessage {
  id: string;
  type: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface ConnectionOptions {
  url?: string;
  autoConnect?: boolean;
  maxRetries?: number;
  retryDelay?: number;
  heartbeatInterval?: number;
}

export interface WebSocketClientState {
  connected: boolean;
  sessionId: string | null;
  messages: AgentMessage[];
  thinking: boolean;
  streaming: boolean;
  error: string | null;
}

export type MessageHandler = (data: WebSocketMessage) => void;
export type ErrorHandler = (error: Error) => void;
export type ConnectionHandler = () => void;
```

---

## 9. 部署和环境配置

### 9.1 开发环境

```json
// package.json
{
  "name": "myagent-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "vite": "^4.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "vitest": "^0.30.0"
  }
}
```

```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom']
        }
      }
    }
  }
});
```

### 9.2 生产环境

```javascript
// 环境配置
const config = {
  development: {
    wsUrl: 'ws://localhost:8080',
    debug: true,
    maxRetries: 3
  },
  production: {
    wsUrl: 'wss://api.yourserver.com/ws',
    debug: false,
    maxRetries: 5
  }
};

export default config[process.env.NODE_ENV || 'development'];
```

### 9.3 Docker 部署

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "preview"]
```

---

## 10. 常见问题和解决方案

### 10.1 连接问题

**Q: WebSocket 连接失败**
```javascript
// 检查连接状态和错误处理
ws.onerror = (error) => {
    console.error('连接错误:', error);
    // 检查网络状态
    if (!navigator.onLine) {
        showError('网络连接已断开');
    }
};
```

**Q: CORS 跨域问题**
```javascript
// 服务端需要正确设置 CORS 头
// 前端使用完整 URL
const ws = new WebSocket('wss://api.example.com/ws');
```

### 10.2 性能问题

**Q: 大量消息导致界面卡顿**
```javascript
// 使用虚拟滚动或分页加载
import { FixedSizeList as List } from 'react-window';

const MessageList = ({ messages }) => (
  <List
    height={400}
    itemCount={messages.length}
    itemSize={60}
    itemData={messages}
  >
    {MessageItem}
  </List>
);
```

**Q: 内存泄漏**
```javascript
// 清理事件监听器和定时器
useEffect(() => {
  const ws = new WebSocket(url);
  
  return () => {
    ws.close();
    clearInterval(heartbeatTimer);
  };
}, []);
```

### 10.3 移动端适配

```css
/* 移动端样式优化 */
@media (max-width: 768px) {
  .chat-container {
    height: 100vh;
    border-radius: 0;
  }
  
  .message {
    max-width: 90%;
    font-size: 16px; /* 防止 iOS 自动缩放 */
  }
  
  .input-form {
    padding: 8px;
    padding-bottom: calc(8px + env(safe-area-inset-bottom));
  }
}
```

---

## 11. 测试指南

### 11.1 单元测试

```javascript
// __tests__/websocket-client.test.js
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { MyAgentClient } from '../src/MyAgentClient';

// Mock WebSocket
global.WebSocket = vi.fn().mockImplementation(() => ({
  send: vi.fn(),
  close: vi.fn(),
  readyState: 1
}));

describe('MyAgentClient', () => {
  let client;
  
  beforeEach(() => {
    client = new MyAgentClient('ws://localhost:8080');
  });
  
  afterEach(() => {
    vi.clearAllMocks();
  });
  
  it('should connect to WebSocket', async () => {
    await client.connect();
    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8080');
  });
  
  it('should handle incoming messages', () => {
    const mockHandler = vi.fn();
    client.onFinalAnswer = mockHandler;
    
    const message = {
      event: 'agent.final_answer',
      content: 'Test response'
    };
    
    client.handleMessage(message);
    expect(mockHandler).toHaveBeenCalledWith(message);
  });
});
```

### 11.2 集成测试

```javascript
// __tests__/integration.test.js  
describe('WebSocket Integration', () => {
  it('should handle full conversation flow', async () => {
    const client = new MyAgentClient();
    const messages = [];
    
    client.onFinalAnswer = (data) => {
      messages.push(data);
    };
    
    await client.connect();
    client.sendMessage('Hello');
    
    // 模拟服务器响应
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    expect(messages).toHaveLength(1);
  });
});
```

---

本文档提供了完整的前端对接指南，包含了从基础连接到高级功能的所有实现细节。开发者可以根据项目需求选择适合的技术栈和实现方案。

如有问题，请参考 [GitHub Issues](https://github.com/your-repo/myagent/issues) 或联系开发团队。