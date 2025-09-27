# Client-Side State Management

本文档介绍 MyAgent WebSocket 框架的客户端状态管理功能，允许客户端保存和恢复会话状态，实现长期离线后的状态恢复。

## 概述

客户端状态管理将会话状态保存在客户端，而不是服务器端。这种方案具有以下优势：

- **用户隐私保护**：状态数据完全由用户控制
- **服务器零存储负担**：服务器保持无状态，降低成本
- **跨设备状态迁移**：用户可以在不同设备间迁移状态
- **离线查看历史**：客户端可以查看历史对话

## 核心组件

### 1. 状态管理器 (StateManager)

`myagent.ws.state_manager.StateManager` 负责：

- 状态序列化和反序列化
- 状态签名和验证
- 敏感信息清理
- 状态完整性检查

### 2. 服务器扩展

`AgentWebSocketServer` 增加了以下功能：

- 状态导出处理
- 状态恢复处理
- 签名验证
- 会话重建

### 3. 协议事件

新增的 WebSocket 事件：

```typescript
// 用户事件
UserEvents.RECONNECT_WITH_STATE = "user.reconnect_with_state"
UserEvents.REQUEST_STATE = "user.request_state"

// 代理事件
AgentEvents.STATE_EXPORTED = "agent.state_exported"
AgentEvents.STATE_RESTORED = "agent.state_restored"
```

## 使用方法

### 服务器端配置

```python
from myagent.ws.server import AgentWebSocketServer

# 创建支持状态管理的服务器
server = AgentWebSocketServer(
    agent_factory_func=create_your_agent,
    host="localhost",
    port=8080,
    state_secret_key="your-secret-key-here"  # 生产环境必须提供固定密钥
)

await server.start_server()
```

### 客户端状态导出

请求导出当前会话状态：

```javascript
// 发送状态导出请求
const exportRequest = {
    event: "user.request_state",
    session_id: "your-session-id",
    timestamp: new Date().toISOString()
};

await websocket.send(JSON.stringify(exportRequest));

// 接收状态导出响应
const response = await receiveMessage();
if (response.event === "agent.state_exported") {
    const signedState = response.metadata.signed_state;
    // 保存到本地存储
    localStorage.setItem(`session_${session_id}`, JSON.stringify(signedState));
}
```

### 客户端状态恢复

使用保存的状态重新连接：

```javascript
// 从本地存储加载状态
const signedState = JSON.parse(localStorage.getItem(`session_${originalSessionId}`));

// 发送状态恢复请求
const restoreRequest = {
    event: "user.reconnect_with_state",
    signed_state: signedState,
    timestamp: new Date().toISOString()
};

await websocket.send(JSON.stringify(restoreRequest));

// 接收恢复确认
const response = await receiveMessage();
if (response.event === "agent.state_restored") {
    const newSessionId = response.session_id;
    console.log(`Session restored: ${newSessionId}`);
    console.log(`Restored step: ${response.metadata.restored_step}`);
    console.log(`Message count: ${response.metadata.message_count}`);
}
```

## 状态结构

### 签名状态格式

```json
{
    "state": {
        "session_id": "original-session-id",
        "current_step": 5,
        "agent_state": "idle",
        "created_at": "2024-01-01T10:00:00Z",
        "last_active_at": "2024-01-01T10:30:00Z",
        "memory_snapshot": "[{\"role\":\"user\",\"content\":\"Hello\"}, ...]",
        "tool_states": {"weather_tool": {"name": "weather_tool", ...}},
        "pending_confirmations": ["step_3_confirm"],
        "metadata": {
            "agent_name": "MyAgent",
            "agent_config": {...},
            "session_state": "idle"
        }
    },
    "timestamp": 1704110400,
    "signature": "abc123...",
    "version": "1.0",
    "checksum": "def456..."
}
```

### 安全机制

1. **HMAC 签名**：使用 SHA-256 HMAC 对状态进行签名
2. **时间戳验证**：防止重放攻击，状态有 7 天有效期
3. **校验和验证**：确保状态完整性
4. **敏感信息清理**：自动移除 API 密钥等敏感数据
5. **大小限制**：限制内存快照大小防止过大状态

## 示例代码

### 完整示例

参考 `examples/client_state_demo.py` 了解完整的客户端实现：

```bash
# 启动测试服务器
python examples/state_test_server.py

# 在另一个终端运行客户端演示
python examples/client_state_demo.py
```

### 自定义客户端

```python
from examples.client_state_demo import MyAgentClient, ClientStateManager

# 创建客户端
client = MyAgentClient("ws://localhost:8080")
await client.connect()

# 创建会话
await client.create_session()

# 发送消息
await client.send_user_message("Hello, what's the weather?")

# 导出状态
signed_state = await client.request_state_export()
client.state_manager.save_state(client.session_id, signed_state)

# 断开连接
await client.disconnect()

# 重新连接并恢复状态
await client.connect()
saved_state = client.state_manager.load_state(original_session_id)
await client.reconnect_with_state(saved_state)

# 继续对话
await client.send_user_message("Do you remember our conversation?")
```

## 最佳实践

### 1. 状态管理

- **定期导出**：在重要操作后导出状态
- **版本控制**：为状态数据添加版本标识
- **压缩存储**：对大状态进行压缩存储
- **清理策略**：定期清理过期状态

### 2. 安全考虑

- **密钥管理**：生产环境使用固定的强密钥
- **传输加密**：使用 WSS (WebSocket Secure)
- **状态加密**：敏感环境下对状态进行额外加密
- **访问控制**：实现用户认证和授权

### 3. 错误处理

```python
try:
    signed_state = await client.request_state_export()
    if signed_state:
        client.state_manager.save_state(session_id, signed_state)
    else:
        logger.warning("State export failed")
except Exception as e:
    logger.error(f"State export error: {e}")
    # 实现重试逻辑
```

### 4. 存储策略

```javascript
// 浏览器环境
class BrowserStateStorage {
    save(sessionId, signedState) {
        try {
            const key = `myagent_session_${sessionId}`;
            const data = {
                signedState,
                savedAt: new Date().toISOString(),
                version: "1.0"
            };
            localStorage.setItem(key, JSON.stringify(data));
        } catch (e) {
            console.error("Failed to save state:", e);
        }
    }
    
    load(sessionId) {
        try {
            const key = `myagent_session_${sessionId}`;
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data).signedState : null;
        } catch (e) {
            console.error("Failed to load state:", e);
            return null;
        }
    }
}
```

## 故障排除

### 常见错误

1. **"Invalid state signature"**
   - 检查服务器密钥配置
   - 确认状态数据未被修改

2. **"State expired"**
   - 状态超过 7 天有效期
   - 需要重新创建会话

3. **"Session already active"**
   - 原会话仍在运行
   - 先取消原会话或使用不同 session_id

4. **"Failed to restore session state"**
   - 检查状态数据完整性
   - 查看服务器日志了解具体错误

### 调试技巧

- 启用详细日志记录
- 检查状态数据大小和格式
- 验证网络连接稳定性
- 确认服务器配置正确

## 限制和注意事项

1. **状态大小限制**：默认最大 100KB，避免过大状态
2. **工具状态限制**：仅恢复基本工具配置，不包含运行时状态
3. **内存快照限制**：最多保留 100 条历史消息
4. **安全依赖**：依赖客户端正确处理状态数据
5. **版本兼容性**：状态格式变更可能导致兼容性问题

## 总结

客户端状态管理为 MyAgent 提供了灵活的会话持久化方案，特别适合注重隐私和简单部署的场景。通过合理的安全机制和最佳实践，可以安全可靠地实现长期会话状态恢复功能。