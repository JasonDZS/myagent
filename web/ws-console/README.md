# @myagent/ws-console

Reusable React components and hooks for MyAgent WebSocket protocol (plan → solve).

Features
- WebSocket client with ACK throttle and auto-reconnect
- Session lifecycle helpers (create, request_state, reconnect_with_state)
- React provider + hook to drive UI
- Drop-in `<MyAgentConsole />` for quick integration

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
  const { state, sendUserMessage, cancel, solveTasks, cancelTask, restartTask, replan, requestState, reconnectWithState } = useMyAgent();
  // ...
}
```

Events and protocol follow docs/ws-server/basic-concepts.md and docs/ws-server/plan_solver_messages.md in this repository.
