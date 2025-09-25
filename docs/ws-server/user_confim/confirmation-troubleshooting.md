# 工具确认功能故障排除指南

## 常见问题及解决方案

### 1. 工具确认请求发送后没有执行

**症状**: 客户端收到确认请求并正确发送响应，但工具没有实际执行

**原因**: step_id 冲突导致确认响应无法正确匹配

**解决方案**: 已在 v1.1 中修复，使用 UUID 生成唯一的确认 step_id

**技术细节**:
```python
# 旧版本 (有问题)
step_id = f"step_{self.step_counter}_confirm_{tool.name}"

# 新版本 (已修复)
import uuid
step_id = f"confirm_{uuid.uuid4().hex[:8]}_{tool.name}"
```

### 1.1 WebSocket消息处理死锁 (关键问题)

**症状**: 客户端发送确认响应，但服务端日志显示从未收到用户响应消息，确认请求永远等待

**原因**: Agent执行和WebSocket消息处理在同一个协程中，`await self._wait_for_user_response()` 阻塞了整个消息处理循环

**死锁流程**:
1. Agent执行工具，请求用户确认
2. `await self._wait_for_user_response()` 阻塞当前协程
3. WebSocket消息接收也在同一协程中，被阻塞
4. 用户响应消息无法被处理
5. 确认永远等不到响应 → 死锁

**解决方案**: 已在 v1.2 中修复，将Agent执行移到独立任务中

**技术细节**:
```python
# 旧版本 (死锁)
elif event_type == UserEvents.MESSAGE and session_id:
    await self._handle_user_message(websocket, session_id, message)

# 新版本 (已修复)  
elif event_type == UserEvents.MESSAGE and session_id:
    # 异步执行，不阻塞消息处理循环
    asyncio.create_task(self._handle_user_message(websocket, session_id, message))
```

**诊断方法**:
- 如果看到确认请求发送但用户响应消息从未到达服务端
- 检查服务端是否有 "User response received" 日志
- 这通常是最常见的确认功能问题

### 2. 确认请求超时

**症状**: 用户已确认但收到超时错误

**可能原因**:
1. step_id 不匹配
2. 网络连接中断
3. WebSocket 消息处理异常

**排查步骤**:
```javascript
// 1. 检查客户端发送的 step_id 是否与收到的一致
console.log('Received step_id:', message.step_id);
console.log('Sending step_id:', step_id);

// 2. 确保 WebSocket 连接正常
if (ws.readyState !== WebSocket.OPEN) {
    console.error('WebSocket connection not open');
}

// 3. 检查响应格式
const response = {
    event: "user.response",
    session_id: sessionId,  // 必须存在
    step_id: stepId,        // 必须与请求中的完全一致
    content: { confirmed: true }
};
```

### 3. 收到"No pending confirmation found"警告

**症状**: 服务端日志显示无法找到待处理的确认请求

**原因**:
1. step_id 不匹配
2. 确认请求已过期或被清理
3. WebSocket 会话重连导致状态丢失

**解决方案**:
```python
# 检查服务端日志中的详细信息
logger.warning(f"No pending confirmation found for step {step_id}")
logger.warning(f"Available pending confirmations: {list(self._pending_confirmations.keys())}")
```

### 4. 工具确认功能不生效

**症状**: 设置了 `user_confirm=True` 但工具直接执行，没有确认请求

**检查清单**:
1. 确保工具正确设置了 `user_confirm=True`
2. 确认工具在 WebSocket 环境中运行
3. 检查工具是否正确继承 `BaseTool`

**正确的工具定义**:
```python
class MyTool(BaseTool):
    name: str = "my_tool"          # 必须有类型注解
    description: str = "My tool"   # 必须有类型注解
    user_confirm: bool = True      # 启用确认
    
    async def execute(self, **kwargs):
        return ToolResult(output="success")
```

### 5. 客户端收不到确认请求

**症状**: 工具设置了确认但客户端没有收到 `agent.user_confirm` 事件

**排查步骤**:
1. 检查 WebSocket 连接状态
2. 确认事件监听器正确设置
3. 检查服务端日志中的确认请求发送记录

**客户端事件处理**:
```javascript
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received event:', message.event); // 调试输出
    
    if (message.event === 'agent.user_confirm') {
        handleConfirmationRequest(message);
    }
};
```

## 调试技巧

### 1. 启用详细日志

在服务端启用详细日志记录：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 或使用 loguru
from loguru import logger
logger.add("debug.log", level="DEBUG")
```

### 2. 客户端调试

在客户端添加详细的消息记录：

```javascript
// 记录所有 WebSocket 消息
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('📥 Received:', message);
    
    // 处理消息...
};

ws.send = function(data) {
    console.log('📤 Sending:', JSON.parse(data));
    WebSocket.prototype.send.call(this, data);
};
```

### 3. 服务端状态检查

添加状态检查端点或日志：

```python
# 在会话中添加调试方法
def debug_pending_confirmations(self):
    logger.info(f"Pending confirmations: {list(self._pending_confirmations.keys())}")
    logger.info(f"Session state: {self.state}")
    logger.info(f"Step counter: {self.step_counter}")
```

## 版本更新说明

### v1.2 修复内容 (重要更新)

1. **修复WebSocket消息处理死锁 (关键修复)**:
   - 将Agent执行移到独立的异步任务中
   - 避免工具确认等待阻塞整个消息处理循环
   - 解决了最常见的确认功能无法工作的问题

2. **改进会话管理**:
   - 修复会话创建过程中的异步调用问题
   - 优化heartbeat清理机制，避免等待确认时会话被误删
   - 增强会话活跃状态检测

3. **优化日志和调试**:
   - 简化日志输出，保留关键信息
   - 添加更好的错误处理和状态追踪

### v1.1 修复内容

1. **修复 step_id 冲突**:
   - 使用 UUID 生成唯一的确认 step_id
   - 避免与工具执行 step_id 的冲突

2. **改进日志记录**:
   - 添加清晰的确认请求和响应日志
   - 简化调试信息输出

3. **增强错误处理**:
   - 更详细的错误信息
   - 改进超时处理逻辑

### 升级建议

如果您使用的是旧版本，建议升级到最新版本以获得以下改进：

1. 更稳定的确认流程
2. 更好的调试信息
3. 减少 step_id 冲突问题

## 性能优化

### 1. 确认超时配置

根据实际需求调整确认超时时间：

```python
# 在 _wait_for_user_response 中调整超时时间
async def _wait_for_user_response(self, step_id: str, timeout: int = 60):  # 60秒
    # ...
```

### 2. 清理过期确认

定期清理过期的确认请求：

```python
async def cleanup_expired_confirmations(self):
    """清理过期的确认请求"""
    current_time = time.time()
    expired_keys = []
    
    for step_id, future in self._pending_confirmations.items():
        if future.done() or current_time - creation_time > timeout:
            expired_keys.append(step_id)
    
    for key in expired_keys:
        self._pending_confirmations.pop(key, None)
```

## 最佳实践

### 1. 客户端最佳实践

- 始终检查 `step_id` 的一致性
- 实现适当的超时处理
- 提供清晰的用户界面
- 记录用户操作用于审计

### 2. 服务端最佳实践

- 为需要确认的工具设置合适的描述
- 实现适当的权限检查
- 记录所有确认操作
- 定期清理过期状态

### 3. 安全考虑

- 验证用户身份后再确认危险操作
- 记录所有确认和拒绝操作
- 对敏感操作实施额外验证
- 定期审计确认日志

通过遵循这些指导原则，您可以确保工具确认功能的稳定运行和安全使用。