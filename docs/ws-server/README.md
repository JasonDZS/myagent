# MyAgent WebSocket 文档中心

## 📚 文档导航

### 🚀 快速开始
- [**WebSocket 模块完整指南**](./ws-guide_zh.md) - ⭐ 推荐！完整的模块使用指南
- [**基础概念**](./basic-concepts.md) - WebSocket协议、事件系统和核心概念
- [**通用协议方案**](./universal-client-protocol.md) - 完整的通用客户端-服务器通信协议
- [**快速开始**](./quick-start.md) - 5分钟上手，支持HTML、Node.js、Python
- [**时序图**](./sequence-diagram.md) - 完整的消息交互流程图

### 🔧 核心功能
- [**用户确认机制**](./user-confirmation.md) - 危险操作的确认流程实现
- [**客户端状态管理**](./client-state-management.md) - 会话状态的客户端存储和恢复
- [**数据可视化集成**](./visualization-integration.md) - ECharts图表可视化支持
- [**Plan & Solve 消息指南**](./plan_solver_messages.md) - 规划/求解流水线与细粒度控制

### 🎯 框架集成
- [**React 集成**](./react-integration.md) - 完整的React Hook和组件实现

## 🎯 选择你的方案

### 我想全面了解 WebSocket 模块
👉 阅读 [**WebSocket 模块完整指南**](./ws-guide_zh.md) - 包含所有核心组件、开发示例和最佳实践

### 我是前端新手
👉 从 [**快速开始**](./quick-start.md) 开始，使用 HTML+JavaScript 版本

### 我使用 React
👉 直接查看 [**React 集成**](./react-integration.md)，获取完整的Hook和组件

### 我使用 Vue
👉 查看 [**数据可视化集成**](./visualization-integration.md)，图表展示功能

### 我需要了解协议细节
👉 阅读 [**基础概念**](./basic-concepts.md) 和 [**通用协议方案**](./universal-client-protocol.md)

### 我需要开发服务器端
👉 查看 [**WebSocket 模块完整指南**](./ws-guide_zh.md) 的服务器端开发章节

### 我的应用需要用户确认
👉 重点关注 [**用户确认机制**](./user-confirmation.md)

### 我需要会话状态持久化
👉 查看 [**客户端状态管理**](./client-state-management.md)，实现离线状态恢复

## ⚡ 核心特性一览

### 🔄 实时双向通信
- WebSocket长连接，低延迟交互
- 自动重连机制，处理网络异常
- 心跳检测，维持连接健康
- 版本兼容的WebSocket工具函数

### 🧠 Agent交互支持
- 思考状态实时显示
- 流式回答，逐步展示结果
- 工具调用过程可视化
- Agent运行时状态跟踪

### ⚠️ 用户确认机制
- 危险操作前强制确认
- 参数详情展示
- 自定义确认消息
- 超时自动取消（5分钟）

### 💾 客户端状态管理
- 会话状态客户端存储（基于 `StateManager`）
- 离线后状态恢复
- HMAC-SHA256 安全签名验证
- 跨设备状态迁移
- 状态有效期（7天）
- 敏感信息自动清理
- 状态大小限制（100KB）

### 🛡️ 可靠性与流控（新增）
- 事件带单调 `seq` 与全局唯一 `event_id`（`<connectionId>-<seq>`）
- 客户端通过 `user.ack` 回传 `last_event_id` 或 `last_seq`，服务端据此裁剪缓冲
- 断线重连可带上次 `last_event_id/last_seq`，服务端按会话缓冲做“差量回放”（最多200条）
- 每连接单写者出站通道与有界队列，避免并发 `send()` 与无界内存
- 高频事件合并：`agent.partial_answer`、`agent.llm_message` 默认75ms窗口仅保留最新

### 📱 多端适配
- 响应式设计，支持移动端
- 完整的键盘快捷键支持
- 可访问性优化

## 📋 事件类型速查

### 用户事件 (发送)
```javascript
user.create_session         // 创建会话
user.message               // 发送消息
user.solve_tasks           // 直接提交任务给求解器（跳过规划）
user.response              // 确认响应（含 step_id）
user.cancel                // 取消当前执行
user.cancel_task           // 取消指定任务（细粒度）
user.restart_task          // 重启指定任务（细粒度）
user.cancel_plan           // 取消规划阶段
user.replan                // 重新规划（会话空闲或运行内重计划）
user.request_state         // 请求导出状态
user.reconnect_with_state  // 使用状态重连
user.ack                   // 客户端ACK，携带 last_event_id 或 last_seq
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
agent.llm_message     // LLM原始消息（调试/可视化）
plan.cancelled        // 规划被取消
solver.cancelled      // 单任务被取消
solver.restarted      // 单任务已重启
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
  // 以下字段由服务器下行事件附带，用于可靠性：
  seq?: number;            // 连接内单调序号
  event_id?: string;       // 全局唯一事件ID: <connectionId>-<seq>
}
```

### 客户端 ACK 建议
- 每收到若干条事件或每200ms发送一次 ACK（节流即可）
- 优先使用 `last_event_id`，无法获取时使用 `last_seq`

示例：
```javascript
// 维护最近收到的 event_id/seq
let lastEventId = null;
let lastSeq = 0;

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (typeof msg.event_id === 'string') lastEventId = msg.event_id;
  if (typeof msg.seq === 'number') lastSeq = msg.seq;
};

// 定时节流 ACK（200ms）
setInterval(() => {
  if (ws.readyState !== WebSocket.OPEN) return;
  const content = lastEventId ? { last_event_id: lastEventId } : { last_seq: lastSeq };
  ws.send(JSON.stringify({ event: 'user.ack', content }));
}, 200);
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

### 直接任务模式（跳过规划）
```javascript
// 在收到 agent.session_created 后：
ws.send(JSON.stringify({
  event: 'user.solve_tasks',
  session_id: data.session_id, // 或缓存的 sessionId
  content: {
    tasks: [{ id: 1, title: '示例', objective: '...' }],
    question: '可选，问题背景',
    plan_summary: '可选，计划摘要'
  }
}));
// 仅会收到 solver.start / solver.completed 等求解相关事件
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
