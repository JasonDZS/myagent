模版型 Agent WebSocket 协议（前端对接说明）

概览
- 通过 WebSocket 暴露“计划 → 执行”流水线：规划器生成章节计划；每个章节由求解器撰写草稿；聚合器按模板原始结构组装最终 Markdown 报告（包含文档标题与层级标题）。
- 服务器入口：`template_agent/server.py`。流水线与工具：`template_agent/src/*.py`。

接入地址
- 默认：ws://127.0.0.1:8081
- 启动命令：`python template_agent/server.py --host 127.0.0.1 --port 8081`
- 会话与连接一一绑定；关闭该 socket 即结束其下所有会话。

消息包裹（Envelope）
- 全部帧均为 JSON 对象，常见字段：
  - `event`：字符串。客户端事件以 `user.` 开头；服务端事件以 `agent.` 或阶段名 `plan.*`/`solver.*`/`aggregate.*` 为主。
  - `session_id`：字符串。除 `user.create_session` 外，客户端消息必填。
  - `content`：任意类型。负载（字符串或对象）。部分事件可为空。
  - `step_id`：字符串。仅服务端在需用户确认时下发（如 `agent.user_confirm`）；前端在 `user.response` 中原样回传。
  - `metadata`：对象。补充上下文（如 `{ "scope": "plan" | "tool" }`）。仅服务端下发。

会话流程
- 创建会话
  - 客户端 → `{ "event": "user.create_session" }`
  - 服务端 → `{ "event": "agent.session_created", "session_id": "<sid>" }`
- 之后所有客户端消息均需携带该 `session_id`。

用户消息（Prompt）
- `user.message` 的 `content` 可为“纯字符串”或“结构化对象”：
  - 字符串：`{ "event": "user.message", "session_id": "<sid>", "content": "你的问题..." }`
  - 结构化对象（推荐）：
    - `{ "event": "user.message", "session_id": "<sid>", "content": { "question": "请基于指定模版与知识库生成报告", "template_name": "商业报告模板", "template_id": "…", "knowledge_base_name": "演示库", "database_id": "…", "api_base_url": "http://127.0.0.1:8787" } }`
- server.py 行为（当 `content` 为对象）：
  - 提取 `question` 作为真正投喂给 Agent 的用户输入。
  - 将以下“提示信息”写入会话上下文，供工具读取：`template_name`、`template_id`、`knowledge_base_name`、`database_id`、`api_base_url`。
  - 服务端会先根据这些提示加载远程资源并构建会话级 VFS；随后 Agent 直接从 VFS 读取模板与数据。
- 校验失败（服务端会下发 `agent.error`）：
  - 会话不存在 / 不属于当前连接
  - `content` 为空

事件时序（Happy Path）
- 规划阶段（Planner）
  - `plan.start` → `content: { question }`
  - 在浏览 VFS 期间会有若干工具事件（如列目录、读文件）：
    - `agent.tool_call` → `metadata: { scope: "plan", tool: <name> }`，`content: { args }`
    - `agent.tool_result` → `content: { output?: string|object, error?: string, system?: string }`
  - 可选：调用 `split_markdown_tree` 预览模板文档树与叶子节点（最小章节）。
  - `plan.completed` → `content: { tasks: [UserSubmittedTask...], plan_summary?: string }`
    - 注意：前端（或 Planner Agent）只需提交“参考文件型任务”，即每个任务仅包含 `id`（叶子顺序 1..N）及其 `required_inputs?`/`hints?`/`notes?`。
    - 系统会基于模板叶子自动填充每个任务的 `title`、`template`（对应该叶子的 Markdown 片段）与 `objective`。
  - 若开启确认（`TEMPLATE_WS_REQUIRE_CONFIRM=true`）：
    - `agent.user_confirm` → 携带 `step_id`，`metadata: { scope: "plan" }`，`content: { message, tasks?: [...] }`
    - 前端应回：`{ "event": "user.response", "session_id": "<sid>", "step_id": "<原样回传>", "content": { "confirmed": true | false, "tasks"?: [...] } }`
- 求解阶段（Solvers，最多并发 `TEMPLATE_WS_CONCURRENCY` 个）
  - `solver.start` → `content: { id, title }`
  - 可穿插工具事件：`agent.tool_call` / `agent.tool_result`（如 `read_local_file`）
  - `solver.completed` → `content: { id, title, summary?: string }`
- 聚合阶段（Aggregator）
  - `aggregate.start`
  - `aggregate.completed` → `content: { output: { sections: [...], report: { content: string, vfs_path?: string, path?: string } } }`
    - 报告正文严格依据模板结构重建：
      - 顶部包含文档标题（YAML front matter 的 `title` 或模板首个 H1，否则使用规划摘要）
      - 保留模板中的标题层级与先后顺序
      - 每个叶子（最小章节）标题下插入对应求解器生成的内容（求解器输出不应重复标题）
- 收尾
  - `pipeline.completed`
  - `agent.final_answer` → 供人阅读的总结。报告正文/路径已在 `aggregate.completed` 给出。
- 错误
  - `agent.error` / `system.error` → `content` 为错误信息（如 `Session not found`、`Agent execution error: ...`）。
  - 心跳：服务端会周期性发送 `system.heartbeat`，`metadata` 中包含活跃会话数等信息；可忽略或用于健康检测。

任务结构说明
- 用户/Planner 提交的任务（简化版，仅用于参考文件）：
  - `id`：整数（1..N，对应模板叶子顺序）
  - `required_inputs?`：字符串数组（VFS 路径，如 `datasets/<file>.json`）
  - `hints?`：字符串数组
  - `notes?`：字符串
- 系统内部用于执行的完整 SectionTask（自动填充）：
  - `id`：整数（1..N）
  - `title`：字符串（来自模板叶子标题）
  - `objective`：字符串（系统生成，要求按模板撰写）
  - `template`：字符串（该叶子在 Markdown 中对应的模板片段）
  - `required_inputs?`/`hints?`/`notes?`：来自用户提交（若有）

章节求解输出（每个章节）
- `{ id: number, title: string, content: string, tables?: any[] }`

聚合输出
- `content.output`：`{ sections: Section[], report: { content: string, vfs_path?: string, path?: string } }`
- 聚合器会把报告写入 VFS `reports/generated_report.md`，并同时返回 `vfs_path` 与兼容字段 `path`。
- 报告正文包含完整文档结构（标题、层级、顺序与模板保持一致）。

- 会话级虚拟文件系统（VFS）
- 基于 pyfilesystem2 的内存文件系统（MemoryFS），按会话隔离。
- 服务端在收到 `user.message` 后会预先加载远程资源并挂载：
  - `template/<name>.md`（Markdown；若原始为 HTML，会做基本转换）
  - `template/<name>.html`（当原始为 HTML 时额外保留）
  - `datasets/<file>.json`（知识库文件）
- Agent 常用工具：
  - `list_local_templates` → 列出 `template/*.md`
  - `list_local_dir { path }` → 列出某个 VFS 目录（如 `datasets`）
  - `read_local_file { path }` → 读取 VFS 文件
  - `split_markdown_tree { path | markdown }` → 解析 Markdown 文档树并给出叶子（最小章节）预览与结构化 JSON

服务端相关环境变量
- `TEMPLATE_WS_CONCURRENCY`（默认 5）：章节求解最大并发。
- `TEMPLATE_WS_BROADCAST_TASKS`（默认 true）：是否在 `plan.completed` 中广播任务列表。
- `TEMPLATE_WS_MAX_RETRY`（默认 1）/ `TEMPLATE_WS_RETRY_DELAY`（默认 3.0）：失败重试策略。
- `TEMPLATE_WS_REQUIRE_CONFIRM`（默认 true）：是否在求解前需要用户确认规划。
- `TEMPLATE_WS_CONFIRM_TIMEOUT`（默认 600）：等待 `user.response` 的超时时间（秒）。

工具/后端相关环境变量
- `TEMPLATE_API_BASE_URL`（优先）或 `TEMPLATE_BACKEND_URL`/`BACKEND_BASE_URL`：服务端预加载远程资源时使用的后端 HTTP 基址。
- `SLM_MODEL`：`summarize_filenames` 使用的小模型名（否则回落到全局 LLM 设置）。

可选用户事件（扩展控制）
- `user.cancel`：取消当前会话内正在执行的流程。
- `user.cancel_task`：取消指定章节求解任务 → `content: { task_id: number }`。
- `user.restart_task`：重启指定章节求解任务 → `content: { task_id: number }`。
- `user.cancel_plan`：取消规划阶段（若在规划中）。
- `user.replan`：在运行中请求“重新规划”，或在空闲时重启一次规划 → `content: { question?: string }`。
- `user.solve_tasks`：跳过规划，直接按给定任务列表运行求解 → `content: { tasks: SectionTask[] | any, question?: string, plan_summary?: string }`。
- `user.request_state`：导出可签名的会话状态（用于断线重连）。
- `user.reconnect_with_state`：携带签名状态重连，服务端会校验并恢复会话。

前端示例
- 创建会话
  - `{ "event": "user.create_session" }`
- 发送结构化用户消息
  - `{ "event": "user.message", "session_id": "<sid>", "content": { "question": "请基于指定模版与知识库生成报告", "template_name": "商业报告模板", "knowledge_base_name": "演示库", "api_base_url": "http://127.0.0.1:8787" } }`
- 确认规划/工具操作
  - `{ "event": "user.response", "session_id": "<sid>", "step_id": "<来自 agent.user_confirm>", "content": { "confirmed": true } }`

自检脚本（E2E）
- 启动后端（默认 http://127.0.0.1:8787）。
- 启动 WS 服务器。
- 执行：`python template_agent/scripts/ws_e2e_check.py --backend http://127.0.0.1:8787 --ws ws://127.0.0.1:8081 --template-name 自检模板 --kb-name 自检知识库`
- 脚本会创建/校验资源，建立会话，发送结构化 `user.message`，在需要时自动确认，并打印报告预览（保存在 VFS 的 `reports/generated_report.md`）。
