import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import '@myagent/ws-console/styles.css';
import { MyAgentProvider, MyAgentConsole, useMyAgent } from '@myagent/ws-console';
import type { WebSocketMessage } from '@myagent/ws-console';
import { ConnectionStatus } from '@myagent/ws-console/components/ConnectionStatus';
import { UserInput } from '@myagent/ws-console/components/UserInput';

const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8080';

function SplitView({ children }: { children: [React.ReactNode, React.ReactNode] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [leftWidth, setLeftWidth] = useState<number>(() => Math.max(200, Math.floor(window.innerWidth * 0.4)));
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const minLeft = 100; // min width px
      const maxLeft = rect.width - 250; // keep right usable
      const next = Math.min(maxLeft, Math.max(minLeft, e.clientX - rect.left));
      setLeftWidth(next);
      e.preventDefault();
    };
    const onUp = () => setDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dragging]);

  return (
    <div ref={containerRef} style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: '#0b0d12' }}>
      <div style={{ width: leftWidth, borderRight: '1px solid #1f2633', background: '#0b0d12' }} />
      <div
        role="separator"
        onMouseDown={() => setDragging(true)}
        style={{ width: 6, cursor: 'col-resize', background: dragging ? '#334155' : '#1f2633' }}
        title="拖拽调整左右布局"
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        {children[1]}
      </div>
    </div>
  );
}

type ThemeOption = 'dark' | 'light';

function ConsolePane({
  sessionId,
  onSessionChange,
  theme,
  onThemeChange,
}: {
  sessionId?: string;
  onSessionChange: (id: string | undefined) => void;
  theme: ThemeOption;
  onThemeChange: (theme: ThemeOption) => void;
}) {
  const { state, createSession, sendUserMessage, cancel, requestState, reconnectWithState } = useMyAgent();
  const sessions = state.availableSessions;
  const activeId = sessionId;
  const isConnected = state.connection === 'connected';

  const optionIds = useMemo(() => {
    const ids = new Set<string>(sessions.map((s) => s.sessionId));
    if (activeId) ids.add(activeId);
    return Array.from(ids);
  }, [sessions, activeId]);

  const handleSelect = useCallback((value: string) => {
    onSessionChange(value ? value : undefined);
  }, [onSessionChange]);

  const handleRestore = useCallback(() => {
    try {
      const raw = typeof localStorage !== 'undefined' ? localStorage.getItem('ma_state_latest') : null;
      if (!raw) return;
      const signed = JSON.parse(raw);
      const last: any = state.lastEventId ? { last_event_id: state.lastEventId } : { last_seq: state.lastSeq };
      reconnectWithState(signed, last);
    } catch (err) {
      console.error('[restore-state]', err);
    }
  }, [reconnectWithState, state.lastEventId, state.lastSeq]);

  const labelFor = useCallback((id: string) => (
    id.length > 18 ? `${id.slice(0, 8)}…${id.slice(-6)}` : id
  ), []);

  const canSend = Boolean(activeId) && isConnected;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="ma-header">
        <div className="ma-header-main">
          <ConnectionStatus status={state.connection} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div className="ma-session-switcher">
              <label className="ma-session-label" htmlFor="ma-session-select">会话</label>
              <select
                id="ma-session-select"
                className="ma-select"
                value={activeId ?? ''}
                onChange={(ev) => handleSelect(ev.target.value)}
              >
                <option value="">请选择会话</option>
                {optionIds.map((id) => (
                  <option key={id} value={id} title={id}>
                    {labelFor(id)}
                  </option>
                ))}
              </select>
            </div>
            <div className="ma-session-switcher">
              <label className="ma-session-label" htmlFor="ma-theme-select">主题</label>
              <select
                id="ma-theme-select"
                className="ma-select"
                value={theme}
                onChange={(ev) => onThemeChange(ev.target.value as ThemeOption)}
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </select>
            </div>
          </div>
        </div>
        <div className="ma-actions">
          <button className="ma-btn" onClick={() => createSession()}>新建会话</button>
          <button className="ma-btn" onClick={() => requestState()} disabled={!activeId}>导出状态</button>
          <button className="ma-btn" onClick={handleRestore} disabled={!activeId}>恢复状态</button>
        </div>
      </div>
      {!activeId && (
        <div className="ma-banner">
          <span className="ma-muted">请选择上方会话或点击“新建会话”开始</span>
        </div>
      )}
      <div style={{ flex: 1, minHeight: 0 }}>
        <MyAgentConsole theme={theme} />
      </div>
      <UserInput
        onSend={(text) => {
          if (!canSend) return;
          sendUserMessage(text);
        }}
        disabled={!canSend}
        generating={!!state.generating}
        onCancel={() => cancel()}
      />
    </div>
  );
}

function App() {
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(undefined);
  const [theme, setTheme] = useState<ThemeOption>('dark');

  const handleEvent = useCallback((event: WebSocketMessage) => {
    if (event.event === 'agent.session_created' && event.session_id) {
      setActiveSessionId(event.session_id);
    }
  }, []);

  return (
    <MyAgentProvider wsUrl={WS_URL} autoReconnect sessionId={activeSessionId} onEvent={handleEvent}>
      <SplitView>
        {[
          <div key="left" />, // 空白左栏
          <ConsolePane
            key="right"
            sessionId={activeSessionId}
            onSessionChange={setActiveSessionId}
            theme={theme}
            onThemeChange={setTheme}
          />,
        ] as [React.ReactNode, React.ReactNode]}
      </SplitView>
    </MyAgentProvider>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
