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
      <div style={{ width: leftWidth, borderRight: '1px solid #1f2633', background: '#0b0d12' }}>
        {children[0]}
      </div>
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

type EventSpec = { label: string; event: string; build: (sessionId?: string) => WebSocketMessage };

function EventCatalog({ sessionId }: { sessionId?: string }) {
  const { injectMessage, selectSession } = useMyAgent();
  const now = () => new Date().toISOString();
  const sid = sessionId ?? 'demo_session';

  const mk = (event: string, content?: any, metadata?: any, extra?: Partial<WebSocketMessage>): WebSocketMessage => ({
    event,
    timestamp: now(),
    session_id: sid,
    content,
    metadata,
    show_content: undefined,
    ...extra,
  });

  const specs: Array<{ category: string; items: EventSpec[] }> = [
    {
      category: 'user.*',
      items: [
        { label: 'user.create_session', event: 'user.create_session', build: () => mk('user.create_session', { project_name: 'Demo' }) },
        { label: 'user.message', event: 'user.message', build: () => mk('user.message', 'Hello from user') },
        { label: 'user.response', event: 'user.response', build: () => mk('user.response', { approved: true }, undefined, { step_id: 'confirm_001' }) },
        { label: 'user.ack', event: 'user.ack', build: () => mk('user.ack', { last_seq: 42 }) },
        { label: 'user.cancel', event: 'user.cancel', build: () => mk('user.cancel', { reason: 'user_request' }) },
        { label: 'user.solve_tasks', event: 'user.solve_tasks', build: () => mk('user.solve_tasks', { tasks: [{ id: 't1', title: 'Task 1' }] }) },
        { label: 'user.cancel_task', event: 'user.cancel_task', build: () => mk('user.cancel_task', { task_id: 't1' }) },
        { label: 'user.restart_task', event: 'user.restart_task', build: () => mk('user.restart_task', { task_id: 't1' }) },
        { label: 'user.cancel_plan', event: 'user.cancel_plan', build: () => mk('user.cancel_plan') },
        { label: 'user.replan', event: 'user.replan', build: () => mk('user.replan', { question: 'Replan this?' }) },
        { label: 'user.request_state', event: 'user.request_state', build: () => mk('user.request_state') },
        { label: 'user.reconnect_with_state', event: 'user.reconnect_with_state', build: () => ({ event: 'user.reconnect_with_state', timestamp: now(), content: { signed_state: { __demo__: true }, last_seq: 10 } as any }) },
      ],
    },
    {
      category: 'plan.*',
      items: [
        { label: 'plan.start', event: 'plan.start', build: () => mk('plan.start', { question: 'Create a 5-slide presentation' }, { plan_id: 'plan_001', timeout_seconds: 120, model: 'gpt-4' }, { step_id: 'plan_001' }) },
        { label: 'plan.completed', event: 'plan.completed', build: () => mk('plan.completed', { tasks: [{ id: 't1', title: 'Slide 1', description: 'Intro' }] }, { task_count: 1, plan_summary: 'One task', total_estimated_tokens: 800, llm_calls: 1, planning_time_ms: 1200, statistics: [{ model: 'gpt-4', input_tokens: 400, output_tokens: 200, origin: 'plan', agent: 'planner' }], metrics: { models: { by_model: { 'gpt-4': { calls: 1, input_tokens: 400, output_tokens: 200 } } } } }, { step_id: 'plan_001' }) },
        { label: 'plan.cancelled', event: 'plan.cancelled', build: () => mk('plan.cancelled', 'Planning cancelled', { reason: 'user_request', cancellation_time_ms: 500 }) },
        { label: 'plan.step_completed', event: 'plan.step_completed', build: () => mk('plan.step_completed', { step_name: 'Outline', step_result: 'ok' }, { step_index: 1, step_duration_ms: 300, tokens_used: 120 }) },
        { label: 'plan.validation_error', event: 'plan.validation_error', build: () => mk('plan.validation_error', { error_message: 'Invalid tasks' }, { error_code: 'ERR_VALIDATION_400', validation_errors: ['tasks required'] }) },
        { label: 'plan.coercion_error', event: 'plan.coercion_error', build: () => mk('plan.coercion_error', 'Failed to coerce tasks', { error_code: 'PLAN_COERCE_001', error_type: 'JSONDecodeError', recovery_action: 'retry', attempt: 1 }) },
      ],
    },
    {
      category: 'solver.*',
      items: [
        { label: 'solver.start', event: 'solver.start', build: () => mk('solver.start', undefined, { task_count: 1, total_tasks: 3, estimated_duration_sec: 60 }, { step_id: 'solve_001' }) },
        { label: 'solver.progress', event: 'solver.progress', build: () => mk('solver.progress', { current_task: 'Slide 2', status: 'processing' }, { progress_percent: 40, current_step: 2, completed_steps: 1, total_steps: 5, elapsed_time_ms: 8500 }, { step_id: 'solve_001' }) },
        { label: 'solver.completed', event: 'solver.completed', build: () => mk('solver.completed', { task: { id: 't1', title: 'Slide 1' }, result: { status: 'success', output: 'Generated slide 1', agent_name: 'solver', model: 'gpt-4' } }, { total_tasks: 1, successful_tasks: 1, failed_tasks: 0, total_execution_time_ms: 45000, total_tokens_used: 600, statistics: [{ model: 'gpt-4', input_tokens: 200, output_tokens: 100, origin: 'solver', agent: 'solver' }] }, { step_id: 'solve_001' }) },
        { label: 'solver.step_failed', event: 'solver.step_failed', build: () => mk('solver.step_failed', { error_message: 'API Timeout', step_name: 'generate' }, { step_index: 2, error_code: 'ERR_EXEC_600', error_type: 'Timeout', recovery_possible: true }, { step_id: 'solve_001' }) },
        { label: 'solver.retry', event: 'solver.retry', build: () => mk('solver.retry', { step_name: 'generate' }, { attempt: 2, max_attempts: 3, backoff_ms: 2000 }, { step_id: 'solve_001' }) },
        { label: 'solver.cancelled', event: 'solver.cancelled', build: () => mk('solver.cancelled', 'Cancelled', { task_id: 't1', reason: 'user_request', execution_time_ms: 12000 }, { step_id: 'solve_001' }) },
        { label: 'solver.restarted', event: 'solver.restarted', build: () => mk('solver.restarted', 'Restart after timeout', { task_id: 't1', previous_error: 'Timeout', attempt: 2, max_attempts: 3, reason: 'retry_after_error', backoff_ms: 2000 }, { step_id: 'solve_001' }) },
      ],
    },
    {
      category: 'agent.*',
      items: [
        { label: 'agent.session_created', event: 'agent.session_created', build: () => mk('agent.session_created', 'Session created', { agent_name: 'demo', agent_type: 'planner' }) },
        { label: 'agent.thinking', event: 'agent.thinking', build: () => mk('agent.thinking', 'Analyzing…', { model: 'gpt-4', max_tokens: 2000, temperature: 0.7, thinking_type: 'planning' }, { step_id: 'plan_001' }) },
        { label: 'agent.tool_call', event: 'agent.tool_call', build: () => mk('agent.tool_call', { tool_name: 'web_search', tool_description: 'Search web', arguments: { query: 'AI 2024' } }, { call_id: 'call_1', tool_type: 'search', estimated_duration_ms: 2000 }, { step_id: 'action_001' }) },
        { label: 'agent.tool_result', event: 'agent.tool_result', build: () => mk('agent.tool_result', { result: { items: 5 }, status: 'success' }, { call_id: 'call_1', execution_time_ms: 1200, tokens_used: 50 }, { step_id: 'action_001' }) },
        { label: 'agent.partial_answer', event: 'agent.partial_answer', build: () => mk('agent.partial_answer', 'Partial text ...', { chunk_index: 1, completion_percent: 20 }, { step_id: 'answer_001' }) },
        { label: 'agent.final_answer', event: 'agent.final_answer', build: () => mk('agent.final_answer', { answer: 'All done.', answer_type: 'text' }, { generation_time_ms: 1800, total_tokens_used: 800, model: 'gpt-4' }, { step_id: 'answer_001' }) },
        { label: 'agent.user_confirm', event: 'agent.user_confirm', build: () => mk('agent.user_confirm', { message: 'Confirm plan', confirmation_type: 'approve', options: [{ id: 'ok', label: 'OK' }] }, { scope: 'plan', tasks: [{ id: 't1', title: 'Slide 1' }], plan_summary: 'One task', critical: false }, { step_id: 'confirm_001' }) },
        { label: 'agent.llm_message', event: 'agent.llm_message', build: () => mk('agent.llm_message', 'Raw token…', { model: 'gpt-4', role: 'assistant', tokens: 1 }, { step_id: 'agent_001' }) },
        { label: 'agent.error', event: 'agent.error', build: () => mk('agent.error', 'Unexpected error') },
        { label: 'agent.interrupted', event: 'agent.interrupted', build: () => mk('agent.interrupted', 'Interrupted by user') },
        { label: 'agent.session_end', event: 'agent.session_end', build: () => mk('agent.session_end', 'Session closed', { reason: 'completion', total_duration_ms: 10000 }) },
        { label: 'agent.state_exported', event: 'agent.state_exported', build: () => mk('agent.state_exported', { exported_state: { demo: true } }, { exported_at: now(), valid_until: now(), state_size_bytes: 256, checksum: 'abc' }) },
        { label: 'agent.state_restored', event: 'agent.state_restored', build: () => mk('agent.state_restored', 'Restored', { restored_at: now(), restoration_time_ms: 500, previous_stage: 'solving', recovered_tasks: 1, state_integrity: 'verified' }) },
      ],
    },
    {
      category: 'system.*',
      items: [
        { label: 'system.connected', event: 'system.connected', build: () => ({ event: 'system.connected', timestamp: now(), content: { server_version: '1.0.0', server_time: now() }, metadata: { server_uptime_seconds: 100, active_sessions: 1 }, connection_id: 'conn_local' }) },
        { label: 'system.heartbeat', event: 'system.heartbeat', build: () => mk('system.heartbeat', { server_time: now() }, { seq: 1, server_uptime_seconds: 200 }) },
        { label: 'system.notice', event: 'system.notice', build: () => mk('system.notice', { message: 'Maintenance soon' }, { type: 'info', severity: 'low' }) },
        { label: 'system.error', event: 'system.error', build: () => mk('system.error', 'System error occurred', { error_code: 'ERR_SYS', severity: 'error' }) },
      ],
    },
    {
      category: 'error.*',
      items: [
        { label: 'error.validation', event: 'error.validation', build: () => mk('error.validation', 'Validation failed', { error_code: 'ERR_VALIDATION_400', field: 'task_count', constraint: '> 0', recoverable: true }) },
        { label: 'error.timeout', event: 'error.timeout', build: () => mk('error.timeout', 'Timeout', { error_code: 'ERR_TIMEOUT_500', timeout_seconds: 30, elapsed_seconds: 31, stage: 'planning', attempt: 1, max_attempts: 3, retry_after_ms: 1000, recovery_strategy: 'retry' }) },
        { label: 'error.execution', event: 'error.execution', build: () => mk('error.execution', 'Execution error', { error_code: 'ERR_EXECUTION_600', error_type: 'RuntimeError', context: {}, recoverable: false }) },
        { label: 'error.retry', event: 'error.retry', build: () => mk('error.retry', 'Retrying', { attempt: 2, max_attempts: 3, delay_ms: 2000, error: 'Timeout' }) },
        { label: 'error.recovery_started', event: 'error.recovery_started', build: () => mk('error.recovery_started', 'Recovery started', { recovery_action: 'retry', estimated_duration_ms: 2000 }) },
        { label: 'error.recovery_success', event: 'error.recovery_success', build: () => mk('error.recovery_success', 'Recovery OK', { recovery_time_ms: 500, attempts: 1 }) },
        { label: 'error.recovery_failed', event: 'error.recovery_failed', build: () => mk('error.recovery_failed', 'Recovery failed', { error_code: 'ERR_RECOVERY', attempts: 3, original_error: 'Timeout', recovery_error: 'RateLimit' }) },
      ],
    },
    {
      category: 'aggregate.* / pipeline.*',
      items: [
        { label: 'aggregate.start', event: 'aggregate.start', build: () => mk('aggregate.start', undefined, { task_count: 3, completed_tasks: 2, failed_tasks: 0 }) },
        { label: 'aggregate.completed', event: 'aggregate.completed', build: () => mk('aggregate.completed', { final_result: { ok: true } }, { aggregation_time_ms: 1000, result_size_bytes: 2048 }) },
        { label: 'pipeline.completed', event: 'pipeline.completed', build: () => mk('pipeline.completed', undefined, { total_time_ms: 180000, plan_time_ms: 45000, solve_time_ms: 120000, aggregate_time_ms: 15000, status: 'success', result_summary: 'Done', statistics: [{ model: 'gpt-4', input_tokens: 1200, output_tokens: 600 }], metrics: { models: { by_model: { 'gpt-4': { calls: 2 } } } } }) },
      ],
    },
  ];

  const [filter, setFilter] = useState('');
  const filtered = useMemo(() => {
    if (!filter) return specs;
    const f = filter.toLowerCase();
    return specs
      .map((g) => ({ ...g, items: g.items.filter((it) => it.event.includes(f) || it.label.toLowerCase().includes(f)) }))
      .filter((g) => g.items.length > 0);
  }, [specs, filter]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '8px 10px', borderBottom: '1px solid #1f2633' }}>
        <div className="ma-muted" style={{ marginBottom: 6 }}>测试事件（点击添加到右侧）</div>
        <input className="ma-inputbox" placeholder="过滤事件名..." value={filter} onChange={(e) => setFilter(e.target.value)} />
        {!sessionId && <div className="ma-muted" style={{ marginTop: 6 }}>提示：请先在右侧创建会话以关联事件</div>}
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {filtered.map((group) => (
          <div key={group.category} style={{ padding: '8px 10px' }}>
            <div className="ma-section-title">{group.category}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 6 }}>
              {group.items.map((spec) => (
                <button
                  key={spec.label}
                  className="ma-btn"
                  style={{ justifyContent: 'flex-start', width: '100%', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                  title={spec.event}
                  onClick={() => {
                    const target = sessionId ?? 'demo_session';
                    if (!sessionId) selectSession(target);
                    const msg = spec.build(target);
                    injectMessage(msg, { sessionId: target });
                  }}
                >
                  {spec.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


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
    const ids = new Set<string>(sessions.map((s: { sessionId: string }) => s.sessionId));
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
        onSend={(text: string) => {
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
          <EventCatalog key="left" sessionId={activeSessionId} />,
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
