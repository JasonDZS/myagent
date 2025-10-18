# MyAgent WebSocket Console - Quick Start Guide

`@myagent/ws-console` is a reusable React component library for integrating MyAgent WebSocket protocol support into your web applications, enabling real-time visualization of Agent execution and backend server interaction.

## Table of Contents

- [Installation](#installation)
- [Basic Integration](#basic-integration)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
- [Example Scenarios](#example-scenarios)
- [Advanced Features](#advanced-features)
- [FAQ](#faq)

---

## Installation

### Using npm/yarn

```bash
npm install @myagent/ws-console react react-dom
# or
yarn add @myagent/ws-console react react-dom
```

### Import Styles

Import CSS in your main entry file:

```tsx
import '@myagent/ws-console/styles.css';
```

---

## Basic Integration

### Minimal Example

```tsx
import React from 'react';
import { MyAgentProvider, MyAgentConsole } from '@myagent/ws-console';
import '@myagent/ws-console/styles.css';

function App() {
  return (
    <MyAgentProvider
      wsUrl="ws://localhost:8080"
      autoReconnect={true}
    >
      <MyAgentConsole theme="dark" />
    </MyAgentProvider>
  );
}

export default App;
```

### Configuration Parameters

#### `MyAgentProvider` Props

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `wsUrl` | `string` | ✓ | - | WebSocket server URL (e.g., `ws://localhost:8080`) |
| `token` | `string` | - | - | Authentication token, passed as URL query parameter |
| `autoReconnect` | `boolean` | - | `true` | Auto-reconnect on connection loss |
| `showSystemLogs` | `boolean` | - | `false` | Display system-level logs (e.g., `system.*` events) |
| `onEvent` | `(m: WebSocketMessage) => void` | - | - | Callback to receive all WebSocket messages |
| `sessionId` | `string` | - | - | Specify or control current session ID |
| `children` | `ReactNode` | ✓ | - | Child components |

#### `MyAgentConsole` Props

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `theme` | `'dark' \| 'light'` | `'dark'` | UI theme |
| `className` | `string` | - | Custom CSS class name |

---

## Core Concepts

### 1. WebSocket Message Architecture

All communication with the backend uses structured `WebSocketMessage`:

```typescript
interface WebSocketMessage {
  event: string;              // Event type (e.g., 'agent.thinking', 'plan.start')
  timestamp: string;          // ISO 8601 timestamp
  session_id?: string;        // Session ID
  step_id?: string;           // Step ID (for correlating responses)
  content?: any;              // Event content
  metadata?: Record<string, any>; // Metadata
  event_id?: string;          // Unique event identifier
  seq?: number;               // Sequence number
}
```

### 2. Event Categories

#### Agent Events (Agent Execution)
- `agent.thinking` - Agent is thinking
- `agent.tool_call` - Calling a tool
- `agent.tool_result` - Tool returned result
- `agent.partial_answer` - Streamed partial answer
- `agent.final_answer` - Final answer
- `agent.user_confirm` - Requires user confirmation
- `agent.error` - Execution error

#### Plan Events (Planning Phase)
- `plan.start` - Planning started
- `plan.completed` - Planning completed
- `plan.cancelled` - Planning cancelled
- `plan.step_completed` - Individual plan step completed

#### Solver Events (Solving Phase)
- `solver.start` - Started solving task
- `solver.progress` - Solving progress update
- `solver.completed` - Task solving completed
- `solver.cancelled` - Task solving cancelled

#### System Events (System Level)
- `system.connected` - Connection established
- `system.heartbeat` - Heartbeat signal
- `system.error` - System error

### 3. Session Management

Each conversation flow corresponds to one session. MyAgent Console supports multi-session management:

```typescript
// Get current state and available sessions
const { state, createSession, selectSession } = useMyAgent();

// state contains:
// - connection: Connection state ('connected' | 'connecting' | 'disconnected' | 'error')
// - messages: Message list of current session
// - availableSessions: All available sessions
// - currentSessionId: Current session ID
// - generating: Whether generating
// - pendingConfirm: Awaiting user confirmation
```

---

## API Reference

### `useMyAgent()` Hook

Use this hook inside `MyAgentProvider` to access Agent state and methods:

```typescript
const {
  // State
  state,                      // AgentConsoleState
  client,                     // AgentWSClient | null

  // Session management
  createSession,              // (content?: any) => void
  selectSession,              // (sessionId: string) => void

  // Message sending
  sendUserMessage,            // (content: any) => void
  sendResponse,               // (stepId: string, content: any) => void
  injectMessage,              // (msg: WebSocketMessage, opts?: {sessionId?: string}) => void

  // Flow control
  cancel,                     // () => void - Cancel current execution
  solveTasks,                 // (tasks: any[], extras?: {...}) => void
  cancelTask,                 // (taskId: string | number) => void
  restartTask,                // (taskId: string | number) => void
  cancelPlan,                 // () => void
  replan,                     // (question?: string) => void

  // State sync
  requestState,               // () => void - Export current state
  reconnectWithState,         // (signedState: any, last?: {...}) => void
} = useMyAgent();
```

#### Common Method Examples

**Send user message:**

```tsx
const { sendUserMessage } = useMyAgent();

sendUserMessage("Please analyze this data");
```

**Confirm/decline operations:**

```tsx
const { sendResponse } = useMyAgent();

// Confirm an operation (using pendingConfirm.step_id)
sendResponse(stepId, { confirmed: true });

// Decline an operation
sendResponse(stepId, { confirmed: false });
```

**Create new session:**

```tsx
const { createSession } = useMyAgent();

createSession({ project_name: "My Project" });
```

**Cancel execution:**

```tsx
const { cancel, cancelPlan, cancelTask } = useMyAgent();

// Cancel all current execution
cancel();

// Or cancel specific task
cancelTask("task_id_123");
```

---

## Example Scenarios

### Scenario 1: Simple Chat Interface

```tsx
import React, { useState } from 'react';
import { MyAgentProvider, MyAgentConsole, useMyAgent } from '@myagent/ws-console';
import '@myagent/ws-console/styles.css';

function ChatApp() {
  return (
    <MyAgentProvider wsUrl="ws://your-server:8080">
      <div style={{ display: 'flex', height: '100vh', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <MyAgentConsole theme="dark" />
        </div>
        <ChatInput />
      </div>
    </MyAgentProvider>
  );
}

function ChatInput() {
  const { sendUserMessage, state } = useMyAgent();
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim()) {
      sendUserMessage(input);
      setInput('');
    }
  };

  return (
    <div style={{ padding: 12, borderTop: '1px solid #eee' }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type message..."
          style={{ flex: 1, padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
        />
        <button
          onClick={handleSend}
          disabled={state.connection !== 'connected'}
          style={{ padding: '8px 16px', cursor: 'pointer' }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatApp;
```

### Scenario 2: Multi-Session Management

```tsx
function MultiSessionApp() {
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>();

  return (
    <MyAgentProvider
      wsUrl="ws://your-server:8080"
      sessionId={activeSessionId}
    >
      <div style={{ display: 'flex', height: '100vh' }}>
        {/* Left sidebar: Session list */}
        <SessionSidebar onSelect={setActiveSessionId} activeId={activeSessionId} />

        {/* Right: Messages and input */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <MyAgentConsole theme="dark" />
          <ChatInput />
        </div>
      </div>
    </MyAgentProvider>
  );
}

function SessionSidebar({ onSelect, activeId }: any) {
  const { state, createSession } = useMyAgent();

  return (
    <div style={{ width: 250, borderRight: '1px solid #eee', padding: 12 }}>
      <button onClick={() => createSession()} style={{ width: '100%', marginBottom: 12 }}>
        New Session
      </button>
      <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
        {state.availableSessions.length} sessions
      </div>
      {state.availableSessions.map((session) => (
        <div
          key={session.sessionId}
          onClick={() => onSelect(session.sessionId)}
          style={{
            padding: 8,
            marginBottom: 4,
            cursor: 'pointer',
            background: activeId === session.sessionId ? '#e0e0e0' : 'transparent',
            borderRadius: 4,
          }}
        >
          <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {session.sessionId}
          </div>
          <div style={{ fontSize: 12, color: '#999' }}>
            {session.messageCount} messages
          </div>
        </div>
      ))}
    </div>
  );
}
```

### Scenario 3: Event Handling and Monitoring

```tsx
function EventHandlerApp() {
  const [planSummary, setPlanSummary] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const handleEvent = (msg: WebSocketMessage) => {
    switch (msg.event) {
      case 'plan.completed':
        setPlanSummary(msg.metadata?.plan_summary || 'Planning completed');
        break;
      case 'agent.error':
      case 'system.error':
        setErrorMsg(msg.content || 'An error occurred');
        break;
      case 'agent.final_answer':
        console.log('Final answer:', msg.content);
        break;
    }
  };

  return (
    <MyAgentProvider
      wsUrl="ws://your-server:8080"
      onEvent={handleEvent}
      showSystemLogs={false}
    >
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {errorMsg && (
          <div style={{ padding: 12, background: '#fee', color: '#c00' }}>
            {errorMsg}
            <button onClick={() => setErrorMsg('')} style={{ marginLeft: 8 }}>Close</button>
          </div>
        )}
        {planSummary && (
          <div style={{ padding: 12, background: '#efe', color: '#060' }}>
            ✓ {planSummary}
          </div>
        )}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <MyAgentConsole theme="dark" />
        </div>
      </div>
    </MyAgentProvider>
  );
}
```

### Scenario 4: Custom Message Injection (For Testing/Demo)

```tsx
function DemoApp() {
  const { injectMessage, selectSession } = useMyAgent();

  const injectPlanEvent = () => {
    const now = new Date().toISOString();
    injectMessage({
      event: 'plan.start',
      timestamp: now,
      session_id: 'demo_session',
      content: { question: 'Create a 5-slide presentation' },
      metadata: { plan_id: 'plan_001' },
    });
  };

  const injectThinkingEvent = () => {
    const now = new Date().toISOString();
    injectMessage({
      event: 'agent.thinking',
      timestamp: now,
      session_id: 'demo_session',
      content: 'Analyzing the request...',
      metadata: { model: 'gpt-4' },
    }, { sessionId: 'demo_session' });
  };

  return (
    <MyAgentProvider wsUrl="ws://your-server:8080">
      <div>
        <div style={{ padding: 12, gap: 8, display: 'flex' }}>
          <button onClick={() => selectSession('demo_session')}>Select Demo Session</button>
          <button onClick={injectPlanEvent}>Inject Plan Event</button>
          <button onClick={injectThinkingEvent}>Inject Thinking Event</button>
        </div>
        <div style={{ height: 'calc(100vh - 60px)' }}>
          <MyAgentConsole theme="dark" />
        </div>
      </div>
    </MyAgentProvider>
  );
}
```

### Scenario 5: Integration with UI Frameworks (Ant Design Example)

```tsx
import { Layout, Input, Button, Card, List, Space } from 'antd';
import { MyAgentProvider, MyAgentConsole, useMyAgent } from '@myagent/ws-console';
import '@myagent/ws-console/styles.css';

const { Header, Sider, Content, Footer } = Layout;

function AntDesignApp() {
  const [sessionId, setSessionId] = useState<string | undefined>();

  return (
    <MyAgentProvider wsUrl="ws://your-server:8080" sessionId={sessionId}>
      <Layout style={{ height: '100vh' }}>
        <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
          <h2>MyAgent Console</h2>
        </Header>
        <Layout style={{ flex: 1 }}>
          <Sider width={250} style={{ background: '#fafafa', borderRight: '1px solid #f0f0f0' }}>
            <SessionList onSelect={setSessionId} activeId={sessionId} />
          </Sider>
          <Content style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
              <Card style={{ height: '100%', overflow: 'hidden' }}>
                <MyAgentConsole theme="light" />
              </Card>
            </div>
            <AgentInput />
          </Content>
        </Layout>
      </Layout>
    </MyAgentProvider>
  );
}

function SessionList({ onSelect, activeId }: any) {
  const { state, createSession } = useMyAgent();

  return (
    <div style={{ padding: 16 }}>
      <Button type="primary" block onClick={() => createSession()} style={{ marginBottom: 16 }}>
        New Session
      </Button>
      <List
        dataSource={state.availableSessions}
        renderItem={(session: any) => (
          <List.Item
            key={session.sessionId}
            onClick={() => onSelect(session.sessionId)}
            style={{
              cursor: 'pointer',
              background: activeId === session.sessionId ? '#e6f7ff' : 'transparent',
              padding: '8px',
              borderRadius: '4px',
            }}
          >
            <List.Item.Meta
              title={session.sessionId.slice(0, 16) + '...'}
              description={`${session.messageCount} messages`}
            />
          </List.Item>
        )}
      />
    </div>
  );
}

function AgentInput() {
  const { sendUserMessage, state } = useMyAgent();
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim()) {
      sendUserMessage(input);
      setInput('');
    }
  };

  return (
    <div style={{ padding: 12, borderTop: '1px solid #f0f0f0' }}>
      <Space.Compact style={{ display: 'flex', width: '100%' }}>
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={handleSend}
          placeholder="Type your message..."
          disabled={state.connection !== 'connected'}
        />
        <Button
          type="primary"
          onClick={handleSend}
          disabled={state.connection !== 'connected' || !input.trim()}
        >
          Send
        </Button>
      </Space.Compact>
    </div>
  );
}

export default AntDesignApp;
```

---

## Advanced Features

### 1. State Export and Restoration

MyAgent Console supports exporting and restoring session state for persistence or cross-browser recovery:

```tsx
function StateManagementExample() {
  const { state, requestState, reconnectWithState } = useMyAgent();

  const exportState = () => {
    requestState();
    // Listen for 'agent.state_exported' event, auto-saves to localStorage
  };

  const restoreState = () => {
    try {
      const raw = localStorage.getItem('ma_state_latest');
      if (!raw) return;
      const signed = JSON.parse(raw);
      const last = {
        last_event_id: state.lastEventId,
        last_seq: state.lastSeq,
      };
      reconnectWithState(signed, last);
    } catch (err) {
      console.error('Failed to restore state:', err);
    }
  };

  return (
    <div>
      <button onClick={exportState}>Export State</button>
      <button onClick={restoreState}>Restore State</button>
    </div>
  );
}
```

### 2. Custom Styling

Components use BEM naming convention, customizable via CSS variables and class names:

```css
/* Override default theme colors */
.ma-theme-dark {
  --ma-bg-primary: #0a0e27;
  --ma-bg-secondary: #1a1f3a;
  --ma-text-primary: #e0e0e0;
  --ma-text-secondary: #888888;
}

/* Customize message styles */
.ma-item {
  padding: 16px !important;
  border-radius: 8px !important;
}

.ma-item.ma-user {
  background: #e3f2fd;
}

.ma-item.ma-system {
  background: #f5f5f5;
}

/* Customize input */
.ma-inputbox {
  border-radius: 8px;
  font-size: 14px;
}
```

### 3. Listen to Connection State Changes

```tsx
function ConnectionStatus() {
  const { state } = useMyAgent();

  return (
    <div>
      Connection Status:
      {state.connection === 'connected' && <span style={{ color: 'green' }}>✓ Connected</span>}
      {state.connection === 'connecting' && <span style={{ color: 'orange' }}>⟳ Connecting...</span>}
      {state.connection === 'disconnected' && <span style={{ color: 'gray' }}>✕ Disconnected</span>}
      {state.connection === 'error' && (
        <span style={{ color: 'red' }}>✗ Error: {state.error}</span>
      )}
    </div>
  );
}
```

### 4. Using Standalone WebSocket Client (Non-React)

If you're in a non-React environment, you can use `AgentWSClient` directly:

```typescript
import { AgentWSClient } from '@myagent/ws-console';

const client = new AgentWSClient({
  url: 'ws://localhost:8080',
  token: 'your-token',
  autoReconnect: true,
  onOpen: () => console.log('Connected'),
  onClose: () => console.log('Disconnected'),
  onError: (err) => console.error('Error:', err),
});

// Listen to messages
const unsubscribe = client.onMessage((msg) => {
  console.log('Received:', msg);
});

// Connect
client.connect();

// Send message
client.send({
  event: 'user.message',
  content: 'Hello Agent',
});

// Get last event info
const { lastEventId, lastSeq } = client.getLastEvent();

// Disconnect
client.disconnect();
```

---

## Event-Driven Component Rendering

One of the most powerful features is using WebSocket events to drive dynamic component rendering. This allows you to respond to agent execution events and render custom UI components based on event data.

### Pattern: Event State Management

Listen to specific events and maintain component state based on event data:

```tsx
import React, { useState, useCallback } from 'react';
import { MyAgentProvider, useMyAgent } from '@myagent/ws-console';
import type { WebSocketMessage } from '@myagent/ws-console';
import '@myagent/ws-console/styles.css';

function EventDrivenApp() {
  return (
    <MyAgentProvider wsUrl="ws://your-server:8080">
      <div style={{ display: 'flex', height: '100vh', gap: 16 }}>
        {/* Left: Console */}
        <div style={{ flex: 1 }}>
          <MyAgentConsole theme="dark" />
        </div>

        {/* Right: Dynamic components based on events */}
        <div style={{ width: 300, borderLeft: '1px solid #eee', padding: 16, overflowY: 'auto' }}>
          <EventPanel />
        </div>
      </div>
    </MyAgentProvider>
  );
}

function EventPanel() {
  const { state } = useMyAgent();
  const [eventResults, setEventResults] = useState<Record<string, any>>({});

  // Handle events
  const handleEvent = useCallback((msg: WebSocketMessage) => {
    switch (msg.event) {
      case 'solver.completed':
        setEventResults(prev => ({
          ...prev,
          solverResult: msg.content,
          solverMetadata: msg.metadata,
        }));
        break;

      case 'plan.completed':
        setEventResults(prev => ({
          ...prev,
          planResult: msg.content,
          planTasks: msg.metadata?.task_count,
        }));
        break;

      case 'agent.tool_result':
        setEventResults(prev => ({
          ...prev,
          toolResults: [...(prev.toolResults || []), msg.content],
        }));
        break;

      case 'agent.final_answer':
        setEventResults(prev => ({
          ...prev,
          finalAnswer: msg.content,
        }));
        break;

      case 'agent.error':
      case 'system.error':
        setEventResults(prev => ({
          ...prev,
          error: msg.content,
        }));
        break;
    }
  }, []);

  // Re-render when connection state or generating state changes
  React.useEffect(() => {
    // You can add custom logic here
  }, [state.connection, state.generating]);

  return (
    <div>
      <h3>Event Results</h3>

      {/* Solver Results */}
      {eventResults.solverResult && (
        <div style={{ marginBottom: 16, padding: 12, background: '#f0f8ff', borderRadius: 4 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8 }}>✓ Solver Completed</div>
          <pre style={{ fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
            {JSON.stringify(eventResults.solverResult, null, 2)}
          </pre>
        </div>
      )}

      {/* Plan Results */}
      {eventResults.planResult && (
        <div style={{ marginBottom: 16, padding: 12, background: '#f0fff0', borderRadius: 4 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8 }}>📋 Plan Completed ({eventResults.planTasks} tasks)</div>
          <pre style={{ fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
            {JSON.stringify(eventResults.planResult, null, 2)}
          </pre>
        </div>
      )}

      {/* Tool Results */}
      {eventResults.toolResults?.length > 0 && (
        <div style={{ marginBottom: 16, padding: 12, background: '#fffaf0', borderRadius: 4 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8 }}>🔧 Tool Results ({eventResults.toolResults.length})</div>
          {eventResults.toolResults.map((result, idx) => (
            <div key={idx} style={{ fontSize: 12, marginBottom: 4 }}>
              <pre style={{ maxHeight: 100, overflow: 'auto' }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}

      {/* Final Answer */}
      {eventResults.finalAnswer && (
        <div style={{ marginBottom: 16, padding: 12, background: '#e8f5e9', borderRadius: 4 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8 }}>🎯 Final Answer</div>
          <div style={{ fontSize: 12 }}>
            {typeof eventResults.finalAnswer === 'object'
              ? JSON.stringify(eventResults.finalAnswer, null, 2)
              : eventResults.finalAnswer}
          </div>
        </div>
      )}

      {/* Error Display */}
      {eventResults.error && (
        <div style={{ marginBottom: 16, padding: 12, background: '#ffebee', borderRadius: 4 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#c62828' }}>⚠️ Error</div>
          <div style={{ fontSize: 12, color: '#b71c1c' }}>
            {typeof eventResults.error === 'object'
              ? JSON.stringify(eventResults.error, null, 2)
              : eventResults.error}
          </div>
        </div>
      )}
    </div>
  );
}

export default EventDrivenApp;
```

### Advanced Pattern: Event Hub with Custom Hooks

Create a custom hook to centralize event handling logic:

```tsx
import { useCallback, useState } from 'react';
import { useMyAgent } from '@myagent/ws-console';
import type { WebSocketMessage } from '@myagent/ws-console';

// Custom hook for event-driven state management
function useEventState() {
  const [eventState, setEventState] = useState({
    solver: { status: 'idle', result: null, error: null },
    plan: { status: 'idle', result: null, taskCount: 0 },
    tools: { results: [], lastCall: null },
    answer: { final: null, partial: [] },
    generation: { active: false, stage: '' },
  });

  const handleEvent = useCallback((msg: WebSocketMessage) => {
    const { event, content, metadata } = msg;

    setEventState(prev => {
      const newState = { ...prev };

      switch (event) {
        // Solver events
        case 'solver.start':
          newState.solver = { status: 'running', result: null, error: null };
          newState.generation.stage = 'solving';
          break;
        case 'solver.progress':
          newState.solver = {
            ...prev.solver,
            result: { progress: metadata?.progress_percent, ...content },
          };
          break;
        case 'solver.completed':
          newState.solver = {
            status: 'completed',
            result: content,
            error: null,
          };
          break;
        case 'solver.cancelled':
          newState.solver = {
            status: 'cancelled',
            result: null,
            error: content || 'Cancelled by user',
          };
          break;

        // Plan events
        case 'plan.start':
          newState.plan = { status: 'running', result: null, taskCount: 0 };
          newState.generation.stage = 'planning';
          break;
        case 'plan.completed':
          newState.plan = {
            status: 'completed',
            result: content,
            taskCount: metadata?.task_count || 0,
          };
          break;
        case 'plan.cancelled':
          newState.plan = {
            status: 'cancelled',
            result: null,
            taskCount: 0,
          };
          break;

        // Tool events
        case 'agent.tool_call':
          newState.tools.lastCall = { name: content?.tool_name, ...content };
          break;
        case 'agent.tool_result':
          newState.tools.results = [
            ...prev.tools.results,
            { call: prev.tools.lastCall, result: content },
          ];
          break;

        // Answer events
        case 'agent.partial_answer':
          newState.answer.partial = [
            ...prev.answer.partial,
            content,
          ];
          break;
        case 'agent.final_answer':
          newState.answer.final = content;
          newState.generation.active = false;
          break;

        // Generation status
        case 'agent.thinking':
          newState.generation.active = true;
          newState.generation.stage = 'thinking';
          break;
        case 'agent.error':
        case 'system.error':
          newState.generation.active = false;
          break;
      }

      return newState;
    });
  }, []);

  return { eventState, handleEvent };
}

// Usage example
function AdvancedEventApp() {
  const { eventState, handleEvent } = useEventState();

  return (
    <MyAgentProvider
      wsUrl="ws://your-server:8080"
      onEvent={handleEvent}
    >
      <div style={{ display: 'flex', height: '100vh', gap: 16 }}>
        <div style={{ flex: 1 }}>
          <MyAgentConsole theme="dark" />
        </div>

        <div style={{ width: 350, borderLeft: '1px solid #eee', padding: 16, overflowY: 'auto' }}>
          {/* Solver Status */}
          <StatusCard
            title="Solver"
            status={eventState.solver.status}
            data={eventState.solver.result}
            error={eventState.solver.error}
          />

          {/* Plan Status */}
          <StatusCard
            title={`Plan (${eventState.plan.taskCount} tasks)`}
            status={eventState.plan.status}
            data={eventState.plan.result}
          />

          {/* Tools Used */}
          {eventState.tools.results.length > 0 && (
            <ToolResultsCard results={eventState.tools.results} />
          )}

          {/* Answer Progress */}
          {eventState.answer.partial.length > 0 && (
            <PartialAnswerCard partials={eventState.answer.partial} />
          )}

          {/* Final Answer */}
          {eventState.answer.final && (
            <FinalAnswerCard answer={eventState.answer.final} />
          )}
        </div>
      </div>
    </MyAgentProvider>
  );
}

function StatusCard({ title, status, data, error }: any) {
  const statusColors = {
    idle: '#999',
    running: '#ff9800',
    completed: '#4caf50',
    cancelled: '#f44336',
  };

  return (
    <div style={{
      marginBottom: 16,
      padding: 12,
      border: `2px solid ${statusColors[status as keyof typeof statusColors]}`,
      borderRadius: 4,
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 8 }}>
        {title}: <span style={{ color: statusColors[status as keyof typeof statusColors] }}>
          {status.toUpperCase()}
        </span>
      </div>
      {error && <div style={{ color: '#f44336', fontSize: 12 }}>{error}</div>}
      {data && (
        <pre style={{ fontSize: 11, maxHeight: 150, overflow: 'auto' }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

function ToolResultsCard({ results }: any) {
  return (
    <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
      <div style={{ fontWeight: 'bold', marginBottom: 8 }}>🔧 Tools Used ({results.length})</div>
      {results.map((item: any, idx: number) => (
        <div key={idx} style={{ fontSize: 11, marginBottom: 8, padding: 8, background: '#fff', borderRadius: 2 }}>
          <div style={{ color: '#1976d2' }}>Tool: {item.call?.tool_name}</div>
          <pre style={{ maxHeight: 80, overflow: 'auto', margin: '4px 0' }}>
            {JSON.stringify(item.result, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  );
}

function PartialAnswerCard({ partials }: any) {
  return (
    <div style={{ marginBottom: 16, padding: 12, background: '#fff3e0', borderRadius: 4 }}>
      <div style={{ fontWeight: 'bold', marginBottom: 8 }}>📝 Partial Answer</div>
      <div style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {partials.join('')}
      </div>
    </div>
  );
}

function FinalAnswerCard({ answer }: any) {
  return (
    <div style={{ marginBottom: 16, padding: 12, background: '#e8f5e9', borderRadius: 4 }}>
      <div style={{ fontWeight: 'bold', marginBottom: 8 }}>🎯 Final Answer</div>
      <div style={{ fontSize: 12 }}>
        {typeof answer === 'object' ? JSON.stringify(answer, null, 2) : answer}
      </div>
    </div>
  );
}

export default AdvancedEventApp;
```

### Real-World Example: Task Progress Dashboard

```tsx
function TaskProgressDashboard() {
  const [tasks, setTasks] = useState<Record<string, any>>({});

  const handleEvent = useCallback((msg: WebSocketMessage) => {
    switch (msg.event) {
      case 'solver.start':
        setTasks(prev => ({
          ...prev,
          [msg.step_id || 'main']: {
            status: 'running',
            startTime: new Date(),
            progress: 0,
          },
        }));
        break;

      case 'solver.progress':
        const taskId = msg.step_id || 'main';
        setTasks(prev => ({
          ...prev,
          [taskId]: {
            ...prev[taskId],
            progress: msg.metadata?.progress_percent || 0,
            currentStep: msg.content?.current_task,
            elapsed: msg.metadata?.elapsed_time_ms,
          },
        }));
        break;

      case 'solver.completed':
        setTasks(prev => ({
          ...prev,
          [msg.step_id || 'main']: {
            ...prev[msg.step_id || 'main'],
            status: 'completed',
            endTime: new Date(),
            result: msg.content,
          },
        }));
        break;

      case 'solver.cancelled':
        setTasks(prev => ({
          ...prev,
          [msg.step_id || 'main']: {
            ...prev[msg.step_id || 'main'],
            status: 'cancelled',
          },
        }));
        break;
    }
  }, []);

  return (
    <MyAgentProvider wsUrl="ws://your-server:8080" onEvent={handleEvent}>
      <div style={{ padding: 20 }}>
        <h2>Task Progress Dashboard</h2>
        {Object.entries(tasks).map(([taskId, task]) => (
          <TaskProgressBar key={taskId} taskId={taskId} task={task} />
        ))}
      </div>
    </MyAgentProvider>
  );
}

function TaskProgressBar({ taskId, task }: any) {
  const statusIcons = {
    running: '⏳',
    completed: '✓',
    cancelled: '✕',
    error: '!',
  };

  return (
    <div style={{ marginBottom: 20, padding: 16, border: '1px solid #ddd', borderRadius: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ fontWeight: 'bold' }}>
          {statusIcons[task.status as keyof typeof statusIcons]} {taskId}
        </div>
        <div style={{ fontSize: 12, color: '#666' }}>
          {task.progress}% · {task.elapsed && `${(task.elapsed / 1000).toFixed(1)}s`}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{
        width: '100%',
        height: 8,
        background: '#e0e0e0',
        borderRadius: 4,
        overflow: 'hidden',
        marginBottom: 8,
      }}>
        <div
          style={{
            height: '100%',
            width: `${task.progress}%`,
            background: task.status === 'completed' ? '#4caf50' : '#2196f3',
            transition: 'width 0.3s',
          }}
        />
      </div>

      {/* Current step */}
      {task.currentStep && (
        <div style={{ fontSize: 12, color: '#666' }}>
          Currently: {task.currentStep}
        </div>
      )}

      {/* Result */}
      {task.result && (
        <pre style={{ fontSize: 11, background: '#f5f5f5', padding: 8, borderRadius: 2 }}>
          {JSON.stringify(task.result, null, 2)}
        </pre>
      )}
    </div>
  );
}

export { TaskProgressDashboard };
```

### Key Patterns Summary

| Pattern | Use Case | Example Event |
|---------|----------|---|
| **State Tracking** | Track execution state across events | Plan starts → completes |
| **Progress Updates** | Show real-time progress | `solver.progress` with `progress_percent` |
| **Result Rendering** | Display specific event results | `solver.completed` with result data |
| **Error Handling** | Show and track errors | `agent.error`, `system.error` |
| **Multi-Step Workflow** | Coordinate multiple stages | Plan → Solve → Aggregate |
| **UI Synchronization** | Keep UI in sync with backend | Disable buttons during generation |

---

## FAQ

### Q: How to handle WebSocket authentication?

**A:** Pass authentication token via `token` parameter. The component automatically appends `?token=xxx` to the WebSocket URL:

```tsx
<MyAgentProvider
  wsUrl="ws://your-server:8080"
  token="your-jwt-token"
>
  {/* ... */}
</MyAgentProvider>
```

### Q: How to filter message types?

**A:** Use the `onEvent` callback:

```tsx
<MyAgentProvider
  wsUrl="ws://your-server:8080"
  onEvent={(msg) => {
    if (msg.event?.startsWith('agent.')) {
      // Handle agent events
    }
  }}
>
  {/* ... */}
</MyAgentProvider>
```

### Q: How to customize message display?

**A:** Modify the `MessageItem` component or override default styles with CSS. See `src/components/MessageItem.tsx` for rendering logic.

### Q: How to debug connection failures?

**A:** Enable `onEvent` and check `system.error` events:

```tsx
onEvent={(msg) => {
  if (msg.event?.includes('error')) {
    console.error('[Event Error]', msg);
  }
}}
```

Also check the browser console Network tab for WebSocket connection status.

### Q: Does it support offline mode?

**A:** Yes. Use the `injectMessage` API to inject locally-generated messages for testing or demos:

```tsx
const { injectMessage } = useMyAgent();

injectMessage({
  event: 'agent.thinking',
  timestamp: new Date().toISOString(),
  content: 'Thinking...',
});
```

### Q: How to use in Next.js/SSR?

**A:** Use dynamic imports to avoid SSR issues:

```tsx
import dynamic from 'next/dynamic';

const MyAgentConsole = dynamic(
  () => import('@myagent/ws-console').then(m => m.MyAgentConsole),
  { ssr: false }
);

export default function Page() {
  return (
    <MyAgentProvider wsUrl="ws://...">
      <MyAgentConsole theme="dark" />
    </MyAgentProvider>
  );
}
```

### Q: Can I use it in Vue/Angular?

**A:** `@myagent/ws-console` is a React component and cannot be directly used in Vue/Angular. However, you can use `AgentWSClient` to build adapter components for these frameworks.

### Q: Which browsers are supported?

**A:** All modern browsers supporting WebSocket and ES6+. We recommend the latest versions of Chrome, Firefox, Safari, or Edge.

---

## Full Example Project

See `example/src/main.tsx` for a complete runnable example including:
- Multi-session management
- Event injection and demo
- Theme switching
- State export/restore
- Custom event handling

Run the example:

```bash
cd example
npm install
npm run dev
```

Then visit `http://localhost:5173`

---

## Support and Contribution

For issues or suggestions, please submit an Issue or Pull Request.

## License

MIT
