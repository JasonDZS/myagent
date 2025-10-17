# 在其他项目中复用 `MyAgentConsole`

`MyAgentConsole` 是一个基于 React 的现成控制台界面，内部依赖 `MyAgentProvider` 管理 WebSocket 会话和消息流。按照下面步骤，把组件安装并嵌入到任意支持 React 17/18 的项目中。

## 1. 安装依赖

```bash
npm install @myagent/ws-console lucide-react
# 或使用 pnpm / yarn，命令等效
```

> `lucide-react` 是图标库，`MyAgentConsole` 在消息列表和状态栏中会引用它的若干图标。

## 2. 引入样式文件

组件内置深色（`dark`）和浅色（`light`）主题，通过同一份 `styles.css` 提供。将打包出来的样式文件引入到应用入口（如 `App.tsx` 或 `index.tsx`）：

```tsx
import '@myagent/ws-console/styles.css';
```

引入后，可在渲染组件时通过 `theme` 属性切换主题，默认值为 `dark`。如果需要进一步定制，可在自定义样式中覆写 `.ma-*` 相关的 CSS 变量或类名。

## 3. 包裹 `MyAgentProvider`

`MyAgentProvider` 负责创建 WebSocket 客户端、维护会话状态，并通过上下文向控制台组件和自定义 Hook 暴露操作能力。需要把当前会话的 `sessionId` 作为属性传入：

```tsx
import { useCallback, useState } from 'react';
import { MyAgentProvider, type WebSocketMessage } from '@myagent/ws-console';

function Providers({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string>();

  const handleEvent = useCallback((event: WebSocketMessage) => {
    if (event.event === 'agent.session_created' && event.session_id) {
      setSessionId(event.session_id);
    }
  }, []);

  return (
    <MyAgentProvider
      wsUrl="wss://your-agent-server/ws"
      token={process.env.AGENT_TOKEN}
      autoReconnect
      showSystemLogs={false}
      onEvent={handleEvent}
      sessionId={sessionId}
    >
      {children}
    </MyAgentProvider>
  );
}
```

- `wsUrl`：必填，指向 Agent WebSocket 服务地址。
- `token`：选填，附加在连接请求中的身份凭证。
- `autoReconnect`：默认 `true`，断线后自动重连。
- `showSystemLogs`：为 `true` 时保留 `system.*` 类型的消息。
- `onEvent`：可选回调，收到任意服务端消息时触发，可结合 `agent.session_created` 更新外部的 `sessionId`。
- `sessionId`：外部控制当前正在查看/交互的会话 ID。

## 4. 渲染控制台

`MyAgentConsole` 负责渲染指定 `sessionId` 的消息列表与确认弹窗，不再自带输入框和会话管理。你可以在外部组合头部、输入框等 UI（`web/ws-console/example` 提供了完整示例）。控制器组件示例：

```tsx
import React, { useCallback, useState } from 'react';
import { MyAgentProvider, MyAgentConsole, useMyAgent, type WebSocketMessage } from '@myagent/ws-console';
import { UserInput } from '@myagent/ws-console/components/UserInput';

function ConsoleShell() {
  const { state, createSession, sendUserMessage, cancel } = useMyAgent();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 560 }}>
      <button onClick={() => createSession()}>新建会话</button>
      <MyAgentConsole />
      <UserInput
        onSend={(text) => sendUserMessage(text)}
        disabled={state.connection !== 'connected' || !state.currentSessionId}
        generating={state.generating}
        onCancel={() => cancel()}
      />
    </div>
  );
}

export default function AgentPage() {
  const [sessionId, setSessionId] = useState<string>();
  const handleEvent = useCallback((event: WebSocketMessage) => {
    if (event.event === 'agent.session_created' && event.session_id) {
      setSessionId(event.session_id);
    }
  }, []);

  return (
    <MyAgentProvider wsUrl="wss://your-agent-server/ws" sessionId={sessionId} onEvent={handleEvent}>
      <ConsoleShell />
    </MyAgentProvider>
  );
}
```

所有消息依旧基于 Zustand 缓存在浏览器 `localStorage` 中，刷新页面后仍可查看历史。

## 5. 扩展自定义行为

除了直接使用控制台，还可以通过 `useMyAgent()` 访问底层能力，构建自定义 UI 或增加业务逻辑：

```tsx
import { useMyAgent } from '@myagent/ws-console';

function CustomFooter() {
  const { state, createSession, selectSession, sendUserMessage, cancel, solveTasks } = useMyAgent();

  return (
    <footer>
      当前连接：{state.connection}
      <div>
        历史会话数量：{state.availableSessions.length}
        {state.availableSessions.map((session) => (
          <button key={session.sessionId} onClick={() => selectSession(session.sessionId)}>
            查看 {session.sessionId}
          </button>
        ))}
      </div>
      <button onClick={() => createSession()}>新建会话</button>
      <button onClick={() => sendUserMessage({ text: 'ping' })}>发送消息</button>
      <button onClick={() => cancel()}>停止当前流程</button>
      <button onClick={() => solveTasks([{ task_id: 'custom', description: 'Run job' }])}>
        下发任务
      </button>
    </footer>
  );
}
```

常用字段和方法：

- `state.messages`：当前 `sessionId` 对应的服务端事件数组，`MyAgentConsole` 会自动渲染。
- `state.generating`：计划、聚合、工具调用或「思考中」状态的组合标记。
- `state.availableSessions`：本地缓存的会话列表（按照最近更新时间排序）。
- `state.viewSessionId`：当前查看的会话 ID（可能与 `state.currentSessionId` 不同）。
- `sendUserMessage(content)`：向当前会话推送用户消息。
- `sendResponse(stepId, content)`：对确认步骤 (`agent.user_confirm`) 发送反馈。
- `selectSession(sessionId)`：切换正在查看的会话历史。
- `reconnectWithState(signedState, last?)`：将导出的签名状态重新写回服务器，实现恢复。

## 6. 构建与发布（可选）

项目内置 `tsup` 配置，可在本仓库执行：

```bash
cd web/ws-console
npm run build
```

命令会在 `dist/` 下产出 ESM/CJS/类型声明及样式文件。复用时有两种常见方式：

### 方式 A：本地路径依赖

如果在 monorepo 内自用，可在目标项目中直接引用本地路径：

```bash
npm install --save ../web/ws-console
# 或使用 npm link/pnpm/yarn workspace 功能
```

这样即使不发布到 npm，也能在多个项目之间复用同一套组件与样式。

### 方式 B：通过 Git 仓库安装

将 `web/ws-console` 目录推送到内部 Git 仓库后，可在其他项目内通过 Git URL 安装：

```bash
npm install git+https://github.com/JasonDZS/myagent.git#subdirectory=web/ws-console
```

- 确保 `package.json`、`dist/` 等发布产物已提交到仓库，或在仓库中配置 `prepare`/`postinstall` 脚本自动执行 `npm run build`。
- Git 安装默认会执行 `prepare`，如果当前 `package.json` 没有该脚本，请在推送前运行 `npm run build` 并提交生成的 `dist/` 目录。
