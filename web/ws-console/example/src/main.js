import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import '@myagent/ws-console/styles.css';
import { MyAgentProvider, MyAgentConsole, useMyAgent } from '@myagent/ws-console';
import { ConnectionStatus } from '@myagent/ws-console/components/ConnectionStatus';
import { UserInput } from '@myagent/ws-console/components/UserInput';
const WS_URL = import.meta.env?.VITE_WS_URL || 'ws://localhost:8080';
function SplitView({ children }) {
    const containerRef = useRef(null);
    const [leftWidth, setLeftWidth] = useState(() => Math.max(200, Math.floor(window.innerWidth * 0.4)));
    const [dragging, setDragging] = useState(false);
    useEffect(() => {
        const onMove = (e) => {
            if (!dragging || !containerRef.current)
                return;
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
    return (_jsxs("div", { ref: containerRef, style: { display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: '#0b0d12' }, children: [_jsx("div", { style: { width: leftWidth, borderRight: '1px solid #1f2633', background: '#0b0d12' }, children: children[0] }), _jsx("div", { role: "separator", onMouseDown: () => setDragging(true), style: { width: 6, cursor: 'col-resize', background: dragging ? '#334155' : '#1f2633' }, title: "\u62D6\u62FD\u8C03\u6574\u5DE6\u53F3\u5E03\u5C40" }), _jsx("div", { style: { flex: 1, minWidth: 0 }, children: children[1] })] }));
}
function EventCatalog({ sessionId }) {
    const { injectMessage, selectSession } = useMyAgent();
    const now = () => new Date().toISOString();
    const sid = sessionId ?? 'demo_session';
    const mk = (event, content, metadata, extra) => ({
        event,
        timestamp: now(),
        session_id: sid,
        content,
        metadata,
        show_content: undefined,
        ...extra,
    });
    const specs = [
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
                { label: 'user.reconnect_with_state', event: 'user.reconnect_with_state', build: () => ({ event: 'user.reconnect_with_state', timestamp: now(), content: { signed_state: { __demo__: true }, last_seq: 10 } }) },
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
        if (!filter)
            return specs;
        const f = filter.toLowerCase();
        return specs
            .map((g) => ({ ...g, items: g.items.filter((it) => it.event.includes(f) || it.label.toLowerCase().includes(f)) }))
            .filter((g) => g.items.length > 0);
    }, [specs, filter]);
    return (_jsxs("div", { style: { height: '100%', display: 'flex', flexDirection: 'column' }, children: [_jsxs("div", { style: { padding: '8px 10px', borderBottom: '1px solid #1f2633' }, children: [_jsx("div", { className: "ma-muted", style: { marginBottom: 6 }, children: "\u6D4B\u8BD5\u4E8B\u4EF6\uFF08\u70B9\u51FB\u6DFB\u52A0\u5230\u53F3\u4FA7\uFF09" }), _jsx("input", { className: "ma-inputbox", placeholder: "\u8FC7\u6EE4\u4E8B\u4EF6\u540D...", value: filter, onChange: (e) => setFilter(e.target.value) }), !sessionId && _jsx("div", { className: "ma-muted", style: { marginTop: 6 }, children: "\u63D0\u793A\uFF1A\u8BF7\u5148\u5728\u53F3\u4FA7\u521B\u5EFA\u4F1A\u8BDD\u4EE5\u5173\u8054\u4E8B\u4EF6" })] }), _jsx("div", { style: { flex: 1, overflow: 'auto' }, children: filtered.map((group) => (_jsxs("div", { style: { padding: '8px 10px' }, children: [_jsx("div", { className: "ma-section-title", children: group.category }), _jsx("div", { style: { display: 'grid', gridTemplateColumns: '1fr', gap: 6 }, children: group.items.map((spec) => (_jsx("button", { className: "ma-btn", style: { justifyContent: 'flex-start', width: '100%', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }, title: spec.event, onClick: () => {
                                    const target = sessionId ?? 'demo_session';
                                    if (!sessionId)
                                        selectSession(target);
                                    const msg = spec.build(target);
                                    injectMessage(msg, { sessionId: target });
                                }, children: spec.label }, spec.label))) })] }, group.category))) })] }));
}
function ConsolePane({ sessionId, onSessionChange, theme, onThemeChange, }) {
    const { state, createSession, sendUserMessage, cancel, requestState, reconnectWithState } = useMyAgent();
    const sessions = state.availableSessions;
    const activeId = sessionId;
    const isConnected = state.connection === 'connected';
    const optionIds = useMemo(() => {
        const ids = new Set(sessions.map((s) => s.sessionId));
        if (activeId)
            ids.add(activeId);
        return Array.from(ids);
    }, [sessions, activeId]);
    const handleSelect = useCallback((value) => {
        onSessionChange(value ? value : undefined);
    }, [onSessionChange]);
    const handleRestore = useCallback(() => {
        try {
            const raw = typeof localStorage !== 'undefined' ? localStorage.getItem('ma_state_latest') : null;
            if (!raw)
                return;
            const signed = JSON.parse(raw);
            const last = state.lastEventId ? { last_event_id: state.lastEventId } : { last_seq: state.lastSeq };
            reconnectWithState(signed, last);
        }
        catch (err) {
            console.error('[restore-state]', err);
        }
    }, [reconnectWithState, state.lastEventId, state.lastSeq]);
    const labelFor = useCallback((id) => (id.length > 18 ? `${id.slice(0, 8)}…${id.slice(-6)}` : id), []);
    const canSend = Boolean(activeId) && isConnected;
    return (_jsxs("div", { style: { height: '100%', display: 'flex', flexDirection: 'column' }, children: [_jsxs("div", { className: "ma-header", children: [_jsxs("div", { className: "ma-header-main", children: [_jsx(ConnectionStatus, { status: state.connection }), _jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 12 }, children: [_jsxs("div", { className: "ma-session-switcher", children: [_jsx("label", { className: "ma-session-label", htmlFor: "ma-session-select", children: "\u4F1A\u8BDD" }), _jsxs("select", { id: "ma-session-select", className: "ma-select", value: activeId ?? '', onChange: (ev) => handleSelect(ev.target.value), children: [_jsx("option", { value: "", children: "\u8BF7\u9009\u62E9\u4F1A\u8BDD" }), optionIds.map((id) => (_jsx("option", { value: id, title: id, children: labelFor(id) }, id)))] })] }), _jsxs("div", { className: "ma-session-switcher", children: [_jsx("label", { className: "ma-session-label", htmlFor: "ma-theme-select", children: "\u4E3B\u9898" }), _jsxs("select", { id: "ma-theme-select", className: "ma-select", value: theme, onChange: (ev) => onThemeChange(ev.target.value), children: [_jsx("option", { value: "dark", children: "Dark" }), _jsx("option", { value: "light", children: "Light" })] })] })] })] }), _jsxs("div", { className: "ma-actions", children: [_jsx("button", { className: "ma-btn", onClick: () => createSession(), children: "\u65B0\u5EFA\u4F1A\u8BDD" }), _jsx("button", { className: "ma-btn", onClick: () => requestState(), disabled: !activeId, children: "\u5BFC\u51FA\u72B6\u6001" }), _jsx("button", { className: "ma-btn", onClick: handleRestore, disabled: !activeId, children: "\u6062\u590D\u72B6\u6001" })] })] }), !activeId && (_jsx("div", { className: "ma-banner", children: _jsx("span", { className: "ma-muted", children: "\u8BF7\u9009\u62E9\u4E0A\u65B9\u4F1A\u8BDD\u6216\u70B9\u51FB\u201C\u65B0\u5EFA\u4F1A\u8BDD\u201D\u5F00\u59CB" }) })), _jsx("div", { style: { flex: 1, minHeight: 0 }, children: _jsx(MyAgentConsole, { theme: theme }) }), _jsx(UserInput, { onSend: (text) => {
                    if (!canSend)
                        return;
                    sendUserMessage(text);
                }, disabled: !canSend, generating: !!state.generating, onCancel: () => cancel() })] }));
}
function App() {
    const [activeSessionId, setActiveSessionId] = useState(undefined);
    const [theme, setTheme] = useState('dark');
    const handleEvent = useCallback((event) => {
        if (event.event === 'agent.session_created' && event.session_id) {
            setActiveSessionId(event.session_id);
        }
    }, []);
    return (_jsx(MyAgentProvider, { wsUrl: WS_URL, autoReconnect: true, sessionId: activeSessionId, onEvent: handleEvent, children: _jsx(SplitView, { children: [
                _jsx(EventCatalog, { sessionId: activeSessionId }, "left"),
                _jsx(ConsolePane, { sessionId: activeSessionId, onSessionChange: setActiveSessionId, theme: theme, onThemeChange: setTheme }, "right"),
            ] }) }));
}
createRoot(document.getElementById('root')).render(_jsx(App, {}));
