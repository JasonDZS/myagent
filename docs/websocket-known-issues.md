# WebSocket 通信方案现状问题记录

本文记录当前基于 WebSocket 的 Agent 推送/交互方案在代码实现与运行层面的主要问题与改进方向，便于后续迭代时按优先级治理。

## 背景与现状

- 典型场景：后端 Agent 持续向前端推送消息（思考、工具调用结果、最终答复等），前端偶发上行（确认操作、多轮追加问题、取消等）。
- 当前实现：基于 `websockets` 库的纯 WebSocket 双向通道，服务端维护 `connection_id` 与 `session_id` 映射，事件协议分 `user.* / agent.* / system.*`，支持心跳、取消、状态导出/恢复等；并已引入事件 `seq`/`event_id`、客户端 `user.ack`、以及基于 `last_event_id/last_seq` 的断线差量回放。
  - 关键文件：
    - `myagent/ws/server.py`（服务端、连接/会话管理、心跳）
    - `myagent/ws/session.py`（会话与流式执行、用户确认等待）
    - `myagent/ws/utils.py`（发送/关闭工具函数）
    - `myagent/ws/state_manager.py`（状态签名、校验与恢复）
    - `myagent/ws/outbound.py`（每连接单写者、出站队列与 partial 合并）

## 已发现问题（分领域）

### 1) 并发发送与背压缺失（高优先级）

状态：已在服务端实现“每连接单写者 + 出站队列”。

- 新增 `myagent/ws/outbound.py`，为每个连接创建单独的 `OutboundChannel`（单写者协程 + 有界队列）。
- 服务端所有发送路径改为通过出站队列发送（`myagent/ws/server.py` 中 `_send_event` 统一路由；`AgentSession` 注入 `send_event_func`）。
- 清理：连接关闭/服务关闭时，会关闭对应的 writer 并清空队列。
- 增强：对高频事件（`agent.partial_answer`, `agent.llm_message`）增加 75ms 合并窗口，仅保留最近一条进行批量刷新，显著降低抖动与压力。

- 现象：不同协程可能同时对同一 `websocket.send()` 写出（会话事件与系统心跳并行）。
  - 心跳发送：`AgentWebSocketServer._heartbeat_loop()` 统一通过 `_send_event()` 串行化。
  - 会话事件：`AgentSession._send_event()` 由注入的 `send_event_func` 路由到服务端出站队列。
- 风险：`websockets` 不保证并发 `send()` 安全；慢消费者时无统一的出站背压/丢弃策略，易造成阻塞或异常。
- 直接原因：缺少“每连接单写者”模型（独立 writer 协程 + 出站队列），所有发送应串行化并集中限速/聚合/丢弃。

### 2) 缺少消息确认/去重与断线差量补发（高优先级）

状态：已引入 `seq`/`event_id` 与 `user.ack`，并实现带 `last_event_id/last_seq` 的断线差量回放（内存缓冲）。

- 事件发送前按连接分配单调 `seq` 并注入 `event_id = {connection_id}-{seq}`；见 `myagent/ws/server.py:_send_event`。
- 客户端通过 `user.ack` 回传 `content.last_event_id`（推荐）或 `content.last_seq`，服务端修剪内存缓冲（每连接最多 1000 条）。
- 断线重连：`user.reconnect_with_state` 携带 `last_event_id` 或 `last_seq`，服务端依据“会话级历史缓冲”（最多 1000 条，回放上限 200 条）回放遗漏事件到新连接（事件会以新连接 `seq/event_id` 重写，并切换为新 `session_id`）。

### 3) 流控不足与消息风暴（中高优先级）

状态：通过出站有界队列 + 合并窗口缓解；后续可按需引入更多策略。

- 已做：
  - 有界出站队列（自然背压）。
  - 高频 partial/llm 事件 75ms 窗口合并。
- 待定：
  - 针对特定事件的“仅保留最新”丢弃策略。
  - 客户端基于 `seq` 的节流 ACK（例如每 N 条/每 T 毫秒 ACK 一次）。

### 4) 断线恢复仅为“表层状态”，缺少执行级幂等（中高优先级）

- 现状：`state_manager` 能恢复会话计数、Agent 状态与 memory 等（`myagent/ws/server.py:876` 起），但对“已执行/未完成”的工具调用无幂等与补偿语义。
- 风险：重试/重连后可能重复执行具副作用的步骤（下载/写文件/外部调用），导致不一致。
- 直接原因：缺少基于 `step_id`/幂等键的工具侧去重设计与“从中间点安全续跑”的边界协议。

### 5) 认证与安全加固不足（高优先级/上线必做）

- 现象：未见握手鉴权/JWT 校验、Origin 校验、速率/连接数限制，也未强制 `wss`；`state_secret_key` 在未显式配置时随机生成（`myagent/ws/server.py:48-52`）。
- 风险：
  - 未授权访问、DoS、跨源滥用。
  - 随机密钥导致重启后此前导出的签名状态全部失效，影响用户体验。

### 6) 观测性与可诊断性不足（中优先级）

状态：`get_status()` 暴露了基本的出站队列长度、每连接 `last_seq/last_ack`；后续可补 Prometheus 指标与事件丢弃计数。

### 7) 关闭/清理边界与超时（中优先级）

- 现象：会话关闭时若仍有待确认的 Future（用户确认），`is_active()` 会因 pending-confirmations 返回 True；虽然连接关闭路径会整体清理，但在长时间无响应且连接未断的场景，会话保持“活跃”。
- 风险：闲置资源长期占用。
- 直接原因：未对确认等待设置统一的“超时后自动拒绝+清理”与软回收策略（当前默认 300 秒，但需配合清理与反馈）。

### 8) 消息体大小与序列化控制（中优先级）

- 现象：工具结果/状态导出可能较大；`max_size` 仅限制入站，出站无大小限制与截断策略。
- 风险：前端/网络链路压力过大；浏览器端解析/渲染卡顿。

## 建议的修复与演进

### 短期（1–2 个迭代）

- 引入“每连接单写者”模型：
  - 为每个 `connection_id` 建立 `asyncio.Queue` 出站队列与独立 writer 协程；所有 `send` 统一入队，writer 串行发送（彻底避免并发 `send()`）。
  - 队列设置上限与策略：当达到上限时对 `agent.partial_answer` 采用“仅保留最新”或按窗口合并；对关键事件（`final_answer`、`tool_result`）严禁丢弃。
- 事件协议增强：
  - 事件携带 `event_id` 与单调 `seq`，客户端按 `seq` 去重、乱序矫正；新增 `user.ack` 携带 `last_seq`。
  - 在 `user.reconnect_with_state` 期间提交客户端 `last_seq`，服务端根据缓存做差量补发。
- 节流与聚合：对 partial/LLM 消息做 50–100ms 聚合窗口，显著降噪。
- 安全最小集：
  - 握手鉴权（JWT/子协议），启用 `wss`，Origin 白名单；基础速率限制与最大连接数。
  - 明确配置固定 `STATE_SECRET_KEY`，避免重启失效；必要时支持密钥轮转与版本号。
- 观测性：统一日志上下文（`connection_id/session_id/event_id`），计数指标与错误率监控。

### 中长期（按需）

- 幂等与恢复：对工具层引入幂等键（基于 `step_id`/参数 Hash），支持“已完成步骤跳过/回放 UI 事件但不再执行副作用”。
- 分布式扩展：
  - 出站事件缓存/队列采用共享存储（Redis/NATS/Kafka）以支持多实例重连补发与水平扩展。
  - 连接层 sticky 或基于订阅广播的会话迁移能力。
- 传输模式可切换：
  - 提供 SSE + HTTP POST 模式作为可选：下行流式更易穿透代理/CDN，偶发上行走 POST；对“推送主、上行少”的页面更合适。
  - 保持同一事件协议，减少前后端差异化成本。

## 代码参考位置（便于对照修改）

- 出站串行与合并：`myagent/ws/outbound.py`（`OutboundChannel._writer` / `enqueue` / `_flush_coalesced_after_delay`）。
- 统一发送入口：`myagent/ws/server.py`（`AgentWebSocketServer._send_event`）。
- 心跳发送：`myagent/ws/server.py`（`AgentWebSocketServer._heartbeat_loop`）。
- 会话事件发送：`myagent/ws/session.py`（`AgentSession._send_event`，注入 `send_event_func`）。
- 服务启动：`myagent/ws/server.py`（`AgentWebSocketServer.start_server`）。
- 状态导出/重连恢复：`myagent/ws/server.py`（`_handle_request_state` / `_handle_reconnect_with_state`）。
- 差量回放：`myagent/ws/server.py`（`_replay_events_on_reconnect`）。

## 结语

当前 WebSocket 方案总体适配“持续下行 + 偶发上行”的场景，但要在生产稳定运行，需优先补齐发送串行化/背压、确认与重放、安全与观测性等基础能力。完成上述短期项后，可视业务再评估是否引入 SSE 作为替代/补充，进一步提升可运维性与可扩展性。

## 客户端对接建议（示例）

- ACK：优先使用 `last_event_id`（包含连接与序号），或退回 `last_seq`。
  - 例如：`{"event":"user.ack","content":{"last_event_id":"<connectionId>-<seq>"}}`
  - 或：`{"event":"user.ack","content":{"last_seq":128}}`
  - 建议频率：每 200ms 或每 20 条事件 ACK 一次（即可）。

- 断线重连并差量回放：
  - 将通过 `agent.state_exported` 获取的 `signed_state` 回传，同时附带最近确认的 `last_event_id`（推荐）或 `last_seq`。
  - 例如：
    ```json
    {
      "event": "user.reconnect_with_state",
      "signed_state": { /* 之前导出的 signed_state */ },
      "content": { "last_event_id": "<prevConn>-<seq>" }
    }
    ```
  - 服务端将恢复会话并回放遗漏事件（回放事件会重写为新连接的 `seq/event_id`，并绑定新的 `session_id`）。

## TODO 进度

已完成
- 每连接单写者 + 出站队列：`myagent/ws/outbound.py` 实现，`myagent/ws/server.py` 集成。
- 会话事件走服务端出站队列：`AgentSession` 注入 `send_event_func`（构造于 `server.py`）。
- 心跳经由出站队列串行化，避免与会话事件并发 `send()`。
- 高频 partial 合并：`agent.partial_answer`/`agent.llm_message` 采用 75ms 合并窗口，降低抖动与压力。
- 事件序列化：为每连接注入单调 `seq` 与 `event_id={connection_id}-{seq}`。
- 客户端 ACK：处理 `user.ack` 并按 `last_seq` 修剪每连接内存缓冲（支持 `last_event_id` 作为更精确的标识）。
- 观测增强：`get_status()` 暴露 `outbound_queues`、`last_seq`、`last_ack`。
- 文档更新：本文件已反映以上改动与后续计划。

进行中 / 新增
- 断线差量补发：已支持在 `user.reconnect_with_state` 携带 `last_event_id` 或 `last_seq`，服务端从“会话历史缓冲”按需回放，回放事件会重写为新连接的 `seq/event_id` 并切换为新 `session_id`；当前为进程内内存缓冲，最大 1000 条，回放上限 200 条。

待办
- 持久化/事件存储：引入 Redis/Kafka 等以跨重启/多实例持久缓冲并支持回放。
- 安全加固：JWT/子协议鉴权、Origin 白名单、`wss`、速率限制/最大连接数、固定 `STATE_SECRET_KEY` 与轮转策略。
- 流控策略：队列饱和时针对 partial 采用“仅保留最新”；指定客户端 ACK 频率（每 N 条或 T 毫秒）。
- 工具幂等：基于 `step_id`/参数哈希的去重与补偿，避免副作用重复执行。
- 分布式扩展：sticky session 或共享总线；跨实例会话迁移能力。
- 消息体控制：大 payload 截断/分段传输；工具结果敏感字段脱敏。
- 可观测性：Prometheus 指标（队列长度、丢弃计数、发送延迟、seq gap）、统一 correlation ID 日志。
- 确认生命周期：统一超时配置、超时自动拒绝并发送用户可见提示、闲置会话回收。
- 传输可选：支持 SSE + POST 与 WebSocket 复用同一事件协议按需切换。
- 测试补全：出站队列/合并/seq-ack/重连回放的单元与集成测试。
