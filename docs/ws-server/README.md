# MyAgent WebSocket 文档中心

## 📚 文档导航

### 🚀 快速开始
- [**基础概念**](./basic-concepts.md) - WebSocket协议、事件系统和核心概念
- [**通用协议方案**](./universal-client-protocol.md) - 完整的通用客户端-服务器通信协议
- [**快速开始**](./quick-start.md) - 5分钟上手，支持HTML、Node.js、Python
- [**时序图**](./sequence-diagram.md) - 完整的消息交互流程图

### 🔧 核心功能
- [**用户确认机制**](./user-confirmation.md) - 危险操作的确认流程实现
- [**客户端状态管理**](./client-state-management.md) - 会话状态的客户端存储和恢复
- [**数据可视化集成**](./visualization-integration.md) - ECharts图表可视化支持

### 🎯 框架集成
- [**React 集成**](./react-integration.md) - 完整的React Hook和组件实现

## 🎯 选择你的方案

### 我是前端新手
👉 从 [**快速开始**](./quick-start.md) 开始，使用 HTML+JavaScript 版本

### 我使用 React
👉 直接查看 [**React 集成**](./react-integration.md)，获取完整的Hook和组件

### 我使用 Vue
👉 查看 [**数据可视化集成**](./visualization-integration.md)，图表展示功能

### 我需要了解协议细节
👉 阅读 [**基础概念**](./basic-concepts.md) 和 [**通用协议方案**](./universal-client-protocol.md)

### 我需要通用的WebSocket解决方案
👉 查看 [**通用协议方案**](./universal-client-protocol.md)，获取完整的客户端-服务器通信协议

### 我的应用需要用户确认
👉 重点关注 [**用户确认机制**](./user-confirmation.md)

### 我需要会话状态持久化
👉 查看 [**客户端状态管理**](./client-state-management.md)，实现离线状态恢复

## ⚡ 核心特性一览

### 🔄 实时双向通信
- WebSocket长连接，低延迟交互
- 自动重连机制，处理网络异常
- 心跳检测，维持连接健康

### 🧠 Agent交互支持
- 思考状态实时显示
- 流式回答，逐步展示结果
- 工具调用过程可视化

### ⚠️ 用户确认机制
- 危险操作前强制确认
- 参数详情展示
- 自定义确认消息

### 💾 客户端状态管理
- 会话状态客户端存储
- 离线后状态恢复
- 安全状态签名验证
- 跨设备状态迁移

### 📱 多端适配
- 响应式设计，支持移动端
- 完整的键盘快捷键支持
- 可访问性优化

## 📋 事件类型速查

### 用户事件 (发送)
```javascript
user.create_session        // 创建会话
user.message              // 发送消息  
user.response             // 确认响应
user.cancel               // 取消执行
user.request_state        // 请求导出状态
user.reconnect_with_state // 使用状态重连
```

### Agent事件 (接收)
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

### 系统事件 (接收)
```javascript
system.connected    // 连接确认
system.heartbeat    // 心跳检测
system.error        // 系统错误
```

## 🔧 基础消息格式

```typescript
interface WebSocketMessage {
  event: string;           // 事件类型
  timestamp: string;       // ISO时间戳
  session_id?: string;     // 会话ID (非系统事件必需)
  step_id?: string;        // 步骤ID (用于请求响应关联)
  content?: string | object; // 消息内容
  metadata?: object;       // 元数据
}
```

## 🚀 快速示例

### 基础连接
```javascript
const ws = new WebSocket('ws://localhost:8080');

ws.onopen = () => {
    // 创建会话
    ws.send(JSON.stringify({
        event: 'user.create_session',
        timestamp: new Date().toISOString(),
        content: 'create_session'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
    
    if (data.event === 'agent.session_created') {
        // 发送测试消息
        ws.send(JSON.stringify({
            session_id: data.session_id,
            event: 'user.message',
            timestamp: new Date().toISOString(),
            content: '你好！'
        }));
    }
};
```

### React Hook 使用
```typescript
function ChatApp() {
    const { 
        connected, 
        messages, 
        sendMessage, 
        pendingConfirmation,
        respondToConfirmation 
    } = useMyAgent();

    return (
        <div>
            {messages.map(msg => (
                <div key={msg.id}>{msg.content}</div>
            ))}
            
            {pendingConfirmation && (
                <ConfirmationDialog 
                    confirmation={pendingConfirmation}
                    onConfirm={respondToConfirmation}
                />
            )}
            
            <input onKeyPress={(e) => {
                if (e.key === 'Enter') {
                    sendMessage(e.target.value);
                    e.target.value = '';
                }
            }} />
        </div>
    );
}
```

## 🛟 获取帮助

### 常见问题
查看 [**基础概念文档**](./basic-concepts.md)，了解更多技术细节。

### 问题报告
如果你发现了文档中的错误或需要新功能，请在 GitHub Issues 中反馈。

### 社区支持
加入我们的开发者社区，与其他开发者交流经验。

---

**快速开始** 👉 选择你感兴趣的文档开始吧！