# MyAgent WebSocket React 集成指南

## 概述

本指南提供了在 React 应用中集成 MyAgent WebSocket 的完整实现方案，包括 Hook、组件和最佳实践。

## 快速开始

### 1. 安装依赖

```bash
npm install react react-dom
# 如果使用 TypeScript
npm install -D @types/react @types/react-dom
```

### 2. 基础 Hook

创建 `hooks/useMyAgent.ts`：

```typescript
import { useState, useEffect, useRef, useCallback } from 'react';

interface UseMyAgentOptions {
    url?: string;
    autoConnect?: boolean;
    autoReconnect?: boolean;
}

interface AgentMessage {
    id: string;
    type: 'user' | 'agent' | 'system';
    content: string;
    timestamp: Date;
    metadata?: any;
}

interface ConfirmationRequest {
    stepId: string;
    toolName: string;
    toolDescription: string;
    toolArgs: Record<string, any>;
    message: string;
}

export function useMyAgent(options: UseMyAgentOptions = {}) {
    const { 
        url = 'ws://localhost:8080', 
        autoConnect = true,
        autoReconnect = true 
    } = options;

    // 状态管理
    const [connected, setConnected] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [messages, setMessages] = useState<AgentMessage[]>([]);
    const [thinking, setThinking] = useState(false);
    const [streaming, setStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pendingConfirmation, setPendingConfirmation] = useState<ConfirmationRequest | null>(null);

    // Refs
    const wsRef = useRef<WebSocket | null>(null);
    const streamingContentRef = useRef<string>('');
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectCountRef = useRef(0);

    // 消息验证
    const validateMessage = useCallback((data: any) => {
        const systemEvents = ['system.connected', 'system.heartbeat', 'system.error'];
        
        if (!systemEvents.includes(data.event) && !data.session_id) {
            console.warn(`Missing session_id for event: ${data.event}`);
            return false;
        }
        
        return true;
    }, []);

    // 连接函数
    const connect = useCallback(async () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return; // 已经连接
        }

        try {
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setConnected(true);
                setError(null);
                reconnectCountRef.current = 0;
                console.log('✅ WebSocket connected');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (validateMessage(data)) {
                        handleMessage(data);
                    }
                } catch (err) {
                    console.error('Message parsing error:', err);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setError('Connection error');
            };

            ws.onclose = (event) => {
                setConnected(false);
                setSessionId(null);
                console.log('WebSocket closed:', event.code, event.reason);
                
                // 自动重连
                if (autoReconnect && reconnectCountRef.current < 5) {
                    const delay = Math.min(1000 * Math.pow(2, reconnectCountRef.current), 30000);
                    reconnectCountRef.current++;
                    
                    reconnectTimeoutRef.current = setTimeout(() => {
                        console.log(`Attempting reconnect (${reconnectCountRef.current}/5)...`);
                        connect();
                    }, delay);
                }
            };

        } catch (err) {
            setError('Connection failed');
            console.error('Connection error:', err);
        }
    }, [url, autoReconnect, validateMessage]);

    // 消息处理
    const handleMessage = useCallback((data: any) => {
        const { event, session_id, content, metadata, step_id } = data;

        switch (event) {
            case 'system.connected':
                createSession();
                break;

            case 'agent.session_created':
                setSessionId(session_id);
                addMessage({
                    type: 'system',
                    content: '会话创建成功',
                    metadata
                });
                break;

            case 'agent.thinking':
                setThinking(true);
                if (content && content !== '正在思考...') {
                    addMessage({
                        type: 'system',
                        content: `💭 ${content}`,
                        metadata
                    });
                }
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
                    metadata: { ...metadata, step_id }
                });
                break;

            case 'agent.tool_result':
                addMessage({
                    type: 'system',
                    content: `📊 ${content}`,
                    metadata: { ...metadata, step_id }
                });
                break;

            case 'agent.user_confirm':
                setPendingConfirmation({
                    stepId: step_id,
                    toolName: metadata?.tool_name || '',
                    toolDescription: metadata?.tool_description || '',
                    toolArgs: metadata?.tool_args || {},
                    message: content || ''
                });
                break;

            case 'agent.llm_message':
                console.log('收到完整对话记录:', content);
                // 可以触发自定义事件或调用回调
                break;

            case 'agent.error':
            case 'system.error':
                setError(content || '未知错误');
                setThinking(false);
                setStreaming(false);
                break;

            case 'agent.interrupted':
                setThinking(false);
                setStreaming(false);
                addMessage({
                    type: 'system',
                    content: '⚠️ 执行已被中断',
                    metadata
                });
                break;
        }
    }, [streaming]);

    // 添加消息
    const addMessage = useCallback((msg: Omit<AgentMessage, 'id' | 'timestamp'>) => {
        const newMessage: AgentMessage = {
            ...msg,
            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, newMessage]);
    }, []);

    // 更新流式消息
    const updateLastStreamingMessage = useCallback((content: string) => {
        setMessages(prev => {
            const updated = [...prev];
            const lastMsg = updated[updated.length - 1];

            if (lastMsg && lastMsg.type === 'agent' && lastMsg.metadata?.streaming) {
                lastMsg.content = content;
            } else {
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
    }, []);

    // 创建会话
    const createSession = useCallback(() => {
        const message = {
            event: 'user.create_session',
            timestamp: new Date().toISOString(),
            content: 'create_session'
        };
        send(message);
    }, []);

    // 发送消息
    const sendMessage = useCallback((content: string) => {
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
    }, [sessionId, addMessage]);

    // 响应确认
    const respondToConfirmation = useCallback((confirmed: boolean, message?: string) => {
        if (!pendingConfirmation || !sessionId) return;

        const response = {
            session_id: sessionId,
            event: 'user.response',
            step_id: pendingConfirmation.stepId,
            timestamp: new Date().toISOString(),
            content: {
                confirmed: confirmed,
                message: message || (confirmed ? '确认执行' : '用户取消')
            }
        };

        send(response);
        setPendingConfirmation(null);
    }, [pendingConfirmation, sessionId]);

    // 取消执行
    const cancelExecution = useCallback(() => {
        if (!sessionId) return;

        const message = {
            session_id: sessionId,
            event: 'user.cancel',
            timestamp: new Date().toISOString(),
            content: 'cancel'
        };
        send(message);
    }, [sessionId]);

    // 发送消息到服务器
    const send = useCallback((message: any) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
        } else {
            setError('WebSocket 未连接');
        }
    }, []);

    // 断开连接
    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (wsRef.current) {
            wsRef.current.close();
        }
    }, []);

    // 清理消息
    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    // 效果
    useEffect(() => {
        if (autoConnect) {
            connect();
        }

        return () => {
            disconnect();
        };
    }, [connect, disconnect, autoConnect]);

    return {
        // 状态
        connected,
        sessionId,
        messages,
        thinking,
        streaming,
        error,
        pendingConfirmation,
        
        // 操作
        connect,
        disconnect,
        sendMessage,
        cancelExecution,
        respondToConfirmation,
        clearMessages
    };
}
```

### 3. 确认对话框组件

创建 `components/ConfirmationDialog.tsx`：

```tsx
import React, { useState } from 'react';

interface ConfirmationRequest {
    stepId: string;
    toolName: string;
    toolDescription: string;
    toolArgs: Record<string, any>;
    message: string;
}

interface ConfirmationDialogProps {
    confirmation: ConfirmationRequest;
    onConfirm: (confirmed: boolean, message?: string) => void;
    onCancel?: () => void;
}

export function ConfirmationDialog({ 
    confirmation, 
    onConfirm, 
    onCancel 
}: ConfirmationDialogProps) {
    const [customMessage, setCustomMessage] = useState('');
    const [isResponding, setIsResponding] = useState(false);

    const handleConfirm = async (confirmed: boolean) => {
        if (isResponding) return;
        
        setIsResponding(true);
        try {
            onConfirm(confirmed, customMessage || undefined);
        } finally {
            setIsResponding(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleConfirm(true);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            handleConfirm(false);
        }
    };

    return (
        <div className="confirmation-modal" onKeyDown={handleKeyDown}>
            <div className="confirmation-content">
                <h3>⚠️ 确认操作</h3>
                
                <div className="confirmation-details">
                    <div className="detail-item">
                        <strong>工具:</strong> 
                        <span className="tool-name">{confirmation.toolName}</span>
                    </div>
                    
                    <div className="detail-item">
                        <strong>描述:</strong>
                        <span>{confirmation.toolDescription}</span>
                    </div>
                    
                    {Object.keys(confirmation.toolArgs).length > 0 && (
                        <div className="detail-item">
                            <strong>参数:</strong>
                            <pre className="tool-args">
                                {JSON.stringify(confirmation.toolArgs, null, 2)}
                            </pre>
                        </div>
                    )}
                    
                    <div className="confirmation-message">
                        {confirmation.message}
                    </div>
                </div>

                <div className="custom-message">
                    <label htmlFor="customMessage">备注 (可选):</label>
                    <input
                        id="customMessage"
                        type="text"
                        value={customMessage}
                        onChange={(e) => setCustomMessage(e.target.value)}
                        placeholder="添加备注信息..."
                        disabled={isResponding}
                    />
                </div>

                <div className="confirmation-buttons">
                    <button
                        onClick={() => handleConfirm(true)}
                        className="confirm-button"
                        disabled={isResponding}
                        autoFocus
                    >
                        {isResponding ? '⏳ 处理中...' : '✅ 确认执行'}
                    </button>
                    <button
                        onClick={() => handleConfirm(false)}
                        className="cancel-button"
                        disabled={isResponding}
                    >
                        ❌ 取消操作
                    </button>
                </div>

                <div className="shortcut-tips">
                    <small>快捷键: Enter 确认 | Escape 取消</small>
                </div>
            </div>
        </div>
    );
}
```

### 4. 聊天界面组件

创建 `components/ChatInterface.tsx`：

```tsx
import React, { useState, useRef, useEffect } from 'react';
import { useMyAgent } from '../hooks/useMyAgent';
import { ConfirmationDialog } from './ConfirmationDialog';

export function ChatInterface() {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    
    const {
        connected,
        messages,
        thinking,
        streaming,
        error,
        pendingConfirmation,
        sendMessage,
        cancelExecution,
        respondToConfirmation,
        clearMessages
    } = useMyAgent();

    // 自动滚动到底部
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, thinking, streaming]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const content = input.trim();
        if (content && !thinking && !pendingConfirmation) {
            sendMessage(content);
            setInput('');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e as any);
        }
    };

    const isInputDisabled = !connected || thinking || !!pendingConfirmation;

    return (
        <div className="chat-container">
            {/* 状态栏 */}
            <div className="status-bar">
                <div className="connection-status">
                    <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
                        {connected ? '🟢 已连接' : '🔴 未连接'}
                    </span>
                    {error && <span className="error-message">❌ {error}</span>}
                </div>
                
                <div className="controls">
                    <button 
                        onClick={clearMessages}
                        className="clear-button"
                        disabled={messages.length === 0}
                    >
                        🗑️ 清空
                    </button>
                    {thinking && (
                        <button 
                            onClick={cancelExecution}
                            className="cancel-button"
                        >
                            ⏹️ 取消
                        </button>
                    )}
                </div>
            </div>

            {/* 消息列表 */}
            <div className="messages-container">
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
                            {msg.metadata?.step_id && (
                                <div className="message-meta">
                                    Step: {msg.metadata.step_id}
                                </div>
                            )}
                        </div>
                    ))}

                    {thinking && !streaming && !messages.some(m => m.metadata?.streaming) && (
                        <div className="message system thinking">
                            <div className="message-content">
                                💭 Agent 正在思考...
                                <div className="thinking-dots">
                                    <span></span><span></span><span></span>
                                </div>
                            </div>
                        </div>
                    )}
                    
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* 确认对话框 */}
            {pendingConfirmation && (
                <ConfirmationDialog
                    confirmation={pendingConfirmation}
                    onConfirm={respondToConfirmation}
                />
            )}

            {/* 输入区域 */}
            <form onSubmit={handleSubmit} className="input-form">
                <div className="input-container">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={
                            !connected ? "等待连接..." :
                            pendingConfirmation ? "等待用户确认..." :
                            thinking ? "Agent 正在处理..." :
                            "输入您的问题..."
                        }
                        disabled={isInputDisabled}
                        className="message-input"
                        rows={1}
                    />
                    <button
                        type="submit"
                        disabled={isInputDisabled || !input.trim()}
                        className="send-button"
                    >
                        {thinking ? '⏳' : '📤'}
                    </button>
                </div>
                
                {isInputDisabled && (
                    <div className="input-status">
                        {!connected && "等待连接..."}
                        {connected && pendingConfirmation && "请先处理确认请求"}
                        {connected && thinking && !pendingConfirmation && "Agent 正在思考，请稍候..."}
                    </div>
                )}
            </form>
        </div>
    );
}
```

### 5. 样式文件

创建 `styles/ChatInterface.css`：

```css
.chat-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 1000px;
    margin: 0 auto;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
    background: white;
}

/* 状态栏 */
.status-bar {
    padding: 12px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
}

.connection-status {
    display: flex;
    align-items: center;
    gap: 16px;
}

.status-indicator {
    font-weight: 600;
}

.error-message {
    color: #fecaca;
    font-weight: 500;
}

.controls {
    display: flex;
    gap: 8px;
}

.clear-button, .cancel-button {
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: white;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
}

.clear-button:hover, .cancel-button:hover {
    background: rgba(255, 255, 255, 0.3);
}

.clear-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* 消息容器 */
.messages-container {
    flex: 1;
    overflow: hidden;
    position: relative;
}

.messages {
    height: 100%;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

/* 消息样式 */
.message {
    max-width: 85%;
    padding: 16px 20px;
    border-radius: 18px;
    position: relative;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.message.user {
    align-self: flex-end;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-bottom-right-radius: 6px;
}

.message.agent {
    align-self: flex-start;
    background: #f8fafc;
    color: #1f2937;
    border: 1px solid #e2e8f0;
    border-bottom-left-radius: 6px;
}

.message.system {
    align-self: center;
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fcd34d;
    font-size: 14px;
    max-width: 90%;
    border-radius: 12px;
}

.message-content {
    margin-bottom: 8px;
    white-space: pre-wrap;
    word-wrap: break-word;
    line-height: 1.5;
}

.message-time {
    font-size: 11px;
    opacity: 0.7;
    text-align: right;
}

.message-meta {
    font-size: 10px;
    opacity: 0.6;
    margin-top: 4px;
}

.streaming-indicator {
    display: inline-block;
    animation: blink 1s infinite;
    margin-left: 4px;
    color: #3b82f6;
    font-weight: bold;
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
    gap: 4px;
    margin-left: 8px;
}

.thinking-dots span {
    width: 6px;
    height: 6px;
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

/* 输入区域 */
.input-form {
    padding: 20px;
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
}

.input-container {
    display: flex;
    gap: 12px;
    align-items: flex-end;
}

.message-input {
    flex: 1;
    padding: 14px 18px;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    outline: none;
    font-size: 15px;
    font-family: inherit;
    resize: vertical;
    min-height: 50px;
    max-height: 120px;
    transition: border-color 0.2s;
}

.message-input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.message-input:disabled {
    background-color: #f1f5f9;
    color: #64748b;
    cursor: not-allowed;
}

.send-button {
    padding: 14px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-size: 16px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 60px;
}

.send-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-button:disabled {
    background: #94a3b8;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
}

.input-status {
    margin-top: 8px;
    font-size: 13px;
    color: #64748b;
    text-align: center;
}

/* 确认对话框 */
.confirmation-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.75);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    animation: fadeIn 0.2s ease-out;
}

.confirmation-content {
    background: white;
    padding: 32px;
    border-radius: 16px;
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    animation: slideUp 0.3s ease-out;
}

.confirmation-content h3 {
    margin: 0 0 24px 0;
    color: #f59e0b;
    font-size: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.confirmation-details {
    margin-bottom: 24px;
}

.detail-item {
    margin: 16px 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.detail-item strong {
    color: #374151;
    font-weight: 600;
}

.tool-name {
    font-family: 'Monaco', 'Menlo', monospace;
    background: #f3f4f6;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 14px;
}

.tool-args {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 16px;
    border-radius: 8px;
    font-size: 13px;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    font-family: 'Monaco', 'Menlo', monospace;
}

.confirmation-message {
    font-weight: 600;
    color: #1f2937;
    background: #fef3c7;
    padding: 16px;
    border-radius: 8px;
    border-left: 4px solid #f59e0b;
    margin-top: 16px;
}

.custom-message {
    margin-bottom: 24px;
}

.custom-message label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: #374151;
}

.custom-message input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    font-size: 14px;
    transition: border-color 0.2s;
}

.custom-message input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.confirmation-buttons {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    margin-bottom: 16px;
}

.confirm-button, .cancel-button {
    padding: 14px 24px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 120px;
    justify-content: center;
}

.confirm-button {
    background-color: #22c55e;
    color: white;
}

.confirm-button:hover:not(:disabled) {
    background-color: #16a34a;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
}

.cancel-button {
    background-color: #ef4444;
    color: white;
}

.cancel-button:hover:not(:disabled) {
    background-color: #dc2626;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.confirm-button:disabled,
.cancel-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
}

.shortcut-tips {
    text-align: center;
    color: #64748b;
}

/* 动画 */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 响应式设计 */
@media (max-width: 768px) {
    .chat-container {
        height: 100vh;
        border-radius: 0;
        border: none;
    }
    
    .message {
        max-width: 95%;
        padding: 12px 16px;
    }
    
    .confirmation-content {
        padding: 24px;
        margin: 16px;
        max-width: none;
        width: calc(100% - 32px);
    }
    
    .confirmation-buttons {
        flex-direction: column;
    }
    
    .confirm-button, .cancel-button {
        width: 100%;
    }
    
    .status-bar {
        padding: 10px 16px;
        font-size: 13px;
    }
    
    .input-form {
        padding: 16px;
    }
    
    .message-input {
        font-size: 16px; /* 防止 iOS 自动缩放 */
    }
}

/* 滚动条样式 */
.messages::-webkit-scrollbar {
    width: 8px;
}

.messages::-webkit-scrollbar-track {
    background: #f1f5f9;
}

.messages::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
}

.messages::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

.tool-args::-webkit-scrollbar {
    width: 6px;
}

.tool-args::-webkit-scrollbar-track {
    background: #f8fafc;
}

.tool-args::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 3px;
}
```

### 6. 主应用组件

创建 `App.tsx`：

```tsx
import React from 'react';
import { ChatInterface } from './components/ChatInterface';
import './styles/ChatInterface.css';

function App() {
    return (
        <div className="App">
            <ChatInterface />
        </div>
    );
}

export default App;
```

## 高级功能

### 1. 消息历史记录

```typescript
// hooks/useMessageHistory.ts
import { useCallback, useEffect } from 'react';

export function useMessageHistory(sessionId: string | null) {
    const saveMessages = useCallback((messages: AgentMessage[]) => {
        if (sessionId && messages.length > 0) {
            localStorage.setItem(`chat_history_${sessionId}`, JSON.stringify(messages));
        }
    }, [sessionId]);

    const loadMessages = useCallback((): AgentMessage[] => {
        if (!sessionId) return [];
        
        const stored = localStorage.getItem(`chat_history_${sessionId}`);
        return stored ? JSON.parse(stored) : [];
    }, [sessionId]);

    const clearHistory = useCallback(() => {
        if (sessionId) {
            localStorage.removeItem(`chat_history_${sessionId}`);
        }
    }, [sessionId]);

    return { saveMessages, loadMessages, clearHistory };
}
```

### 2. 自动重连管理

```typescript
// hooks/useAutoReconnect.ts
import { useRef, useCallback } from 'react';

export function useAutoReconnect(connect: () => Promise<void>) {
    const reconnectCountRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const scheduleReconnect = useCallback(async () => {
        if (reconnectCountRef.current >= 5) {
            console.error('Max reconnection attempts reached');
            return;
        }

        const delay = Math.min(1000 * Math.pow(2, reconnectCountRef.current), 30000);
        reconnectCountRef.current++;

        console.log(`Scheduling reconnect in ${delay}ms (attempt ${reconnectCountRef.current}/5)`);

        reconnectTimeoutRef.current = setTimeout(async () => {
            try {
                await connect();
                reconnectCountRef.current = 0; // Reset on successful connection
            } catch (error) {
                console.error('Reconnection failed:', error);
                scheduleReconnect(); // Try again
            }
        }, delay);
    }, [connect]);

    const cancelReconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        reconnectCountRef.current = 0;
    }, []);

    return { scheduleReconnect, cancelReconnect };
}
```

## 测试

### 1. 单元测试示例

```typescript
// __tests__/useMyAgent.test.ts
import { renderHook, act } from '@testing-library/react';
import { useMyAgent } from '../hooks/useMyAgent';

// Mock WebSocket
global.WebSocket = jest.fn().mockImplementation(() => ({
    send: jest.fn(),
    close: jest.fn(),
    readyState: WebSocket.OPEN
}));

describe('useMyAgent', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should connect to WebSocket on mount', () => {
        renderHook(() => useMyAgent({ url: 'ws://localhost:8080' }));
        
        expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8080');
    });

    it('should handle incoming messages', async () => {
        const { result } = renderHook(() => useMyAgent());
        
        act(() => {
            // Simulate message received
            const mockMessage = {
                event: 'agent.final_answer',
                session_id: 'test_session',
                content: 'Test response'
            };
            
            // Trigger message handler
            // result.current.handleMessage(mockMessage);
        });
        
        expect(result.current.messages).toHaveLength(1);
    });
});
```

### 2. 集成测试

```typescript
// __tests__/ChatInterface.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from '../components/ChatInterface';

describe('ChatInterface', () => {
    it('should render chat interface', () => {
        render(<ChatInterface />);
        
        expect(screen.getByPlaceholderText(/输入您的问题/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /📤/ })).toBeInTheDocument();
    });

    it('should send message when form is submitted', async () => {
        render(<ChatInterface />);
        
        const input = screen.getByPlaceholderText(/输入您的问题/);
        const sendButton = screen.getByRole('button', { name: /📤/ });
        
        fireEvent.change(input, { target: { value: 'Test message' } });
        fireEvent.click(sendButton);
        
        await waitFor(() => {
            expect(screen.getByText('Test message')).toBeInTheDocument();
        });
    });
});
```

## 部署注意事项

### 1. 环境变量

```typescript
// config/websocket.ts
const config = {
    development: {
        wsUrl: 'ws://localhost:8080',
        reconnectAttempts: 3,
        heartbeatInterval: 30000
    },
    production: {
        wsUrl: process.env.REACT_APP_WS_URL || 'wss://api.yourdomain.com/ws',
        reconnectAttempts: 5,
        heartbeatInterval: 60000
    }
};

export default config[process.env.NODE_ENV as keyof typeof config] || config.development;
```

### 2. 错误边界

```tsx
// components/ErrorBoundary.tsx
import React from 'react';

interface State {
    hasError: boolean;
    error?: Error;
}

export class WebSocketErrorBoundary extends React.Component<
    React.PropsWithChildren<{}>,
    State
> {
    constructor(props: React.PropsWithChildren<{}>) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('WebSocket component error:', error, errorInfo);
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

现在你已经有了完整的 React 集成方案！这个实现包括：

- ✅ 完整的 WebSocket 连接管理
- ✅ 用户确认机制支持
- ✅ 自动重连功能
- ✅ 流式消息处理
- ✅ 响应式设计
- ✅ TypeScript 支持
- ✅ 错误处理
- ✅ 测试示例

## 下一步

- 查看 [用户确认机制详细说明](./user-confirmation.md)
- 了解 [Vue.js 集成方案](./vue-integration.md) 
- 参考 [故障排除指南](./troubleshooting.md)