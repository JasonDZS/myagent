# 在项目中集成 `MyAgentConsole`

`MyAgentConsole` 定义在 `src/components/MyAgentConsole.tsx` 中，只暴露两个可选属性：`className` 与 `theme`（`dark` | `light`）。组件内部通过 `useMyAgent()` 取得由 `MyAgentProvider` 维护的状态，渲染消息列表并在确认步骤（`agent.user_confirm`）触发 `sendResponse`。官方示例 `example/src/main.tsx` 展示了从连接 WebSocket 到构建完整控制台的全过程，下面依次拆解核心环节。

## 1. 安装依赖与样式
- 安装包：`npm install @myagent/ws-console lucide-react`
- 在应用入口引入样式：`import '@myagent/ws-console/styles.css'`
- `styles.css` 同时包含深浅主题，只需在渲染时通过 `theme` 属性切换。
- 若要定制主题，可覆盖 `.ma-console`、`.ma-theme-dark`/`.ma-theme-light` 下的变量或类。

## 2. 准备 Provider（连接与会话）
`MyAgentProvider` 负责打开 WebSocket，跟踪会话，并通过上下文向 `MyAgentConsole`、`UserInput` 等组件提供状态。

关键属性（参考 `example/src/main.tsx`）：
- `wsUrl`：必填，WebSocket 服务地址。示例通过 `VITE_WS_URL` 或 `ws://localhost:8080` 设置。
- `sessionId`：外部控制当前活跃会话。示例中在收到 `agent.session_created` 事件后更新。
- `autoReconnect`：布尔值，启用断线重连（示例启用）。
- `onEvent`：监听所有服务端消息，可用于同步会话或记录日志。
- `token`（可选）：在初始化 `AgentWSClient` 时会拼入连接请求，用于服务端鉴权。
- `showSystemLogs`（可选）：若为 `true`，会保留以 `system.*` 开头的事件并显示在消息流中。

示例化写法：

```tsx
const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8080';

function App() {
  const [sessionId, setSessionId] = useState<string>();

  const handleEvent = useCallback((event: WebSocketMessage) => {
    if (event.event === 'agent.session_created' && event.session_id) {
      setSessionId(event.session_id);
    }
  }, []);

  return (
    <MyAgentProvider wsUrl={WS_URL} sessionId={sessionId} autoReconnect onEvent={handleEvent}>
      {/** 控制台 UI */}
    </MyAgentProvider>
  );
}
```

### MyAgentProvider 行为速览
- 组件首次挂载时会创建 `AgentWSClient`，状态从 `connecting` 流转为 `connected` / `error`，并在卸载时断开连接。
- 所有消息会写入内部的 Zustand `session-store`，默认使用 `localStorage`（键名 `myagent-session-cache`）持久化，刷新后仍可读取。
- 收到 `agent.state_exported` 事件时，会将签名状态持久化到 `localStorage`：`ma_state_<sessionId>` 与 `ma_state_latest`。
- `showSystemLogs={false}` 时会过滤掉 `system.*` 事件，避免噪声干扰 UI。
- 如果你在外部传入 `sessionId`，Provider 会将当前会话切换到该值；未传入时会沿用内部状态或最近一次的会话。

常见扩展点（都通过 `useMyAgent()` 或 `onEvent` 获取）：
- 监听 `connection`/`error` 更新，提示用户重新连接。
- 将 `state.pendingConfirm` 渲染为自定义的确认对话框，并通过 `sendResponse` 反馈。
- 使用 `requestState()` 与 `reconnectWithState()` 完成会话导出 / 恢复。

## 3. 组合控制台 UI
`MyAgentConsole` 只关注消息展示，因此需要结合 `useMyAgent()` 提供的操作拼装完整界面。示例中的 `ConsolePane` 做了以下工作：
- 使用 `ConnectionStatus`、`createSession()` 等实现会话切换与状态指示。
- 通过 `<MyAgentConsole theme={theme} />` 在中间区域呈现消息流。
- 使用 `UserInput` 发送用户消息，并在 `state.generating` 时显示 loading 或调用 `cancel()`。
- 允许用户切换 `dark`/`light` 主题并将选项传给 `MyAgentConsole`。

最小可用组合示例：

```tsx
function ConsolePane() {
  const { state, createSession, sendUserMessage, cancel } = useMyAgent();
  const sessionReady = state.connection === 'connected' && !!state.currentSessionId;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <button onClick={() => createSession()}>新建会话</button>
      <MyAgentConsole theme="dark" />
      <UserInput
        disabled={!sessionReady}
        generating={!!state.generating}
        onSend={(text) => sessionReady && sendUserMessage(text)}
        onCancel={() => cancel()}
      />
    </div>
  );
}
```

## 4. 使用辅助功能
`example/src/main.tsx` 还展示了多个常见增强点：
- 拖拽左右布局：`SplitView` 使用 `ref` 控制可视区域宽度。
- 会话恢复：通过 `requestState()` 导出服务器签名的状态，`reconnectWithState()` 将其写回（示例从 `localStorage` 读取 `ma_state_latest`）。
- 主题切换：外层维护 `theme` 状态并传给 `MyAgentConsole`。
- 会话预览：利用 `state.availableSessions` 填充 `<select>`，实现历史记录回放。

这些能力均来自 `useMyAgent()` 暴露的上下文：
- `state.messages`：当前查看会话的事件列表（`MyAgentConsole` 将其渲染为消息流）。
- `state.generating`：是否有计划/工具调用/回答在进行。
- `state.connection`、`state.lastEventId` 等连接与同步元数据。
- 方法：`createSession`、`selectSession`、`sendUserMessage`、`sendResponse`、`requestState`、`reconnectWithState`、`cancel` 等。

## 5. 运行与调试
- 在本仓库执行 `npm install`、`npm run dev -- --open` 可启动示例页面，直接查看控制台效果。
- 生产环境可执行 `npm run build`，生成的 `dist/` 目录包含组件、类型与样式，可通过 npm、Git 子目录或工作区的方式复用。
- 如果集成到现有项目，请确认构建系统支持处理 `.css` 与 `tsx`/`ts`，并在打包后保留 `@myagent/ws-console/styles.css`。

通过以上步骤，即可在任何 React 项目中快速复用 `MyAgentConsole`，既可以照搬 `example/src/main.tsx` 的完整布局，也可以只保留消息面板，结合自定义的主题、会话调度与输入体验。
