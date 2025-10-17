# @myagent/ws-console

Reusable React components and hooks for MyAgent WebSocket protocol (plan → solve).

Features
- WebSocket client with ACK throttle and auto-reconnect
- Session lifecycle helpers (create, request_state, reconnect_with_state)
- React provider + hook to drive UI
- Drop-in `<MyAgentConsole />` for quick integration
- Built-in dark/light themes configurable via prop
- Local session cache via Zustand with per-session history switching
- Externally controlled sessions via the `sessionId` provider prop

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
import { useCallback, useState } from 'react';
import '@myagent/ws-console/styles.css';
import { MyAgentProvider, MyAgentConsole, type WebSocketMessage } from '@myagent/ws-console';

export default function App() {
  const [sessionId, setSessionId] = useState<string>();

  const handleEvent = useCallback((event: WebSocketMessage) => {
    if (event.event === 'agent.session_created' && event.session_id) {
      setSessionId(event.session_id);
    }
  }, []);

  return (
    <MyAgentProvider wsUrl="ws://localhost:8080" sessionId={sessionId} onEvent={handleEvent}>
      <div style={{ height: 600 }}>
        <MyAgentConsole />
      </div>
    </MyAgentProvider>
  );
}
```

`MyAgentConsole` renders the message list and confirmation prompts for the active session. Compose your own header, composer, and session picker (see `example/` for a full shell) using the commands exposed through `useMyAgent()`.

Appearance
- `MyAgentConsole` accepts a `theme` prop (`'dark' | 'light'`, defaults to `'dark'`).
- CSS variables (`--ma-*`) drive the styling, so you can override colors or define additional themes by wrapping the root element with custom classes.
- Example: `<MyAgentConsole theme="light" />` renders the bundled light palette without any additional CSS.

Sessions & history
- Incoming messages (and local user messages) are cached per session in a persisted Zustand store.
- Pass the desired `sessionId` into `MyAgentProvider`; switching that prop changes which history `MyAgentConsole` displays.
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
  const { state, createSession, selectSession, sendUserMessage, cancel, solveTasks, cancelTask, restartTask, replan, requestState, reconnectWithState } = useMyAgent();

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
      <button onClick={() => createSession()}>新建会话</button>
    </aside>
  );
  // ...
}
```

Events and protocol follow docs/ws-server/basic-concepts.md and docs/ws-server/plan_solver_messages.md in this repository.
