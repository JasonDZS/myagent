# @myagent/ws-console

Reusable React components and hooks for MyAgent WebSocket protocol (plan → solve).

Features
- WebSocket client with ACK throttle and auto-reconnect
- Session lifecycle helpers (create, request_state, reconnect_with_state)
- React provider + hook to drive UI
- Drop-in `<MyAgentConsole />` for quick integration
- Built-in dark/light themes configurable via prop
- Local session cache via Zustand with per-session history switching

Installation
```
npm i @myagent/ws-console
# or
yarn add @myagent/ws-console
```

Icons
- This package uses `lucide-react` for message icons. If your app does not already include it, install:
```
npm i lucide-react
# or
yarn add lucide-react
```

Usage (basic)
```tsx
import '@myagent/ws-console/styles.css';
import { MyAgentProvider, MyAgentConsole } from '@myagent/ws-console';

export default function App() {
  return (
    <MyAgentProvider wsUrl="ws://localhost:8080">
      <div style={{ height: 600 }}>
        <MyAgentConsole />
      </div>
    </MyAgentProvider>
  );
}
```

Appearance
- `MyAgentConsole` accepts a `theme` prop (`'dark' | 'light'`, defaults to `'dark'`).
- CSS variables (`--ma-*`) drive the styling, so you can override colors or define additional themes by wrapping the root element with custom classes.
- Example: `<MyAgentConsole theme="light" />` renders the bundled light palette without any additional CSS.

Sessions & history
- Incoming messages (and local user messages) are cached per session in a persisted Zustand store.
- The header shows a session selector once more than one session exists; choosing an older session switches the message list to that history and temporarily disables the composer.
- `useMyAgent()` exposes `state.availableSessions`, `state.viewSessionId`, and a `selectSession(sessionId)` helper so you can build custom session pickers.

Local example (split view)
- A resizable test page is included: `web/ws-console/example`
- Run it pointing to your WS server (default ws://localhost:8080)

```
cd web/ws-console/example
npm i
npm run dev
# open http://localhost:5173
```

Hook API
```tsx
import { MyAgentProvider, useMyAgent } from '@myagent/ws-console';

function CustomUI() {
  const { state, selectSession, sendUserMessage, cancel, solveTasks, cancelTask, restartTask, replan, requestState, reconnectWithState } = useMyAgent();

  return (
    <aside>
      <p>当前连接：{state.connection}</p>
      <p>当前会话：{state.currentSessionId ?? '无'}</p>
      <ul>
        {state.availableSessions.map((session) => (
          <li key={session.sessionId}>
            <button onClick={() => selectSession(session.sessionId)}>
              查看 {session.sessionId}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
  // ...
}
```

Events and protocol follow docs/ws-server/basic-concepts.md and docs/ws-server/plan_solver_messages.md in this repository.
