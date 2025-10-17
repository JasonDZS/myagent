import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { AgentConsoleState, MyAgentProviderProps, WebSocketMessage } from './types';
import { AgentWSClient } from './ws-client';

interface Ctx {
  state: AgentConsoleState;
  client: AgentWSClient | null;
  // Commands
  createSession: (content?: any) => void;
  sendUserMessage: (content: any) => void;
  sendResponse: (stepId: string, content: any) => void;
  cancel: () => void;
  solveTasks: (tasks: any[], extras?: { question?: string; plan_summary?: string }) => void;
  cancelTask: (taskId: string | number) => void;
  restartTask: (taskId: string | number) => void;
  cancelPlan: () => void;
  replan: (question?: string) => void;
  requestState: () => void;
  reconnectWithState: (signedState: any, last?: { last_event_id?: string; last_seq?: number }) => void;
}

const MyAgentCtx = createContext<Ctx | null>(null);

export function MyAgentProvider(props: MyAgentProviderProps) {
  const { wsUrl, token, autoReconnect = true, showSystemLogs = false, onEvent, children } = props;
  const [state, setState] = useState<AgentConsoleState>({
    connection: 'disconnected',
    messages: [],
    lastEventId: null,
    lastSeq: 0,
    pendingConfirm: null,
    generating: false,
    planRunning: false,
    aggregateRunning: false,
    solverRunning: 0,
    thinking: false,
  });
  const clientRef = useRef<AgentWSClient | null>(null);

  // Lazily construct client to avoid SSR issues
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const client = new AgentWSClient({ url: wsUrl, token, autoReconnect, onOpen: () => setState((s) => ({ ...s, connection: 'connected', error: null })), onClose: () => setState((s) => ({ ...s, connection: 'disconnected' })), onError: (err) => setState((s) => ({ ...s, connection: 'error', error: String(err) })) });
    clientRef.current = client;
    setState((s) => ({ ...s, connection: 'connecting' }));
    client.connect();
    const off = client.onMessage((m) => {
      onEvent?.(m);
      try {
        if (m.event === 'agent.state_exported') {
          const sid = m.session_id || 'unknown';
          const signed = (m.metadata as any)?.signed_state;
          if (signed && typeof localStorage !== 'undefined') {
            localStorage.setItem(`ma_state_${sid}`, JSON.stringify(signed));
            localStorage.setItem(`ma_state_latest`, JSON.stringify(signed));
          }
        }
      } catch {}
      setState((s) => {
        const lastEventId = typeof m.event_id === 'string' ? m.event_id : s.lastEventId ?? null;
        const lastSeq = typeof (m as any).seq === 'number' ? ((m as any).seq as number) : s.lastSeq ?? 0;
        const nextMessages = (() => {
          if (!showSystemLogs && String(m.event).startsWith('system.')) return s.messages;
          return [...s.messages, m];
        })();
        // runtime counters
        let planRunning = !!s.planRunning;
        let aggregateRunning = !!s.aggregateRunning;
        let solverRunning = Math.max(0, s.solverRunning || 0);
        let thinking = !!s.thinking;
        const ev = String(m.event || '');
        switch (ev) {
          case 'plan.start':
            planRunning = true; thinking = false; break;
          case 'plan.completed':
          case 'plan.cancelled':
            planRunning = false; thinking = false; break;
          case 'solver.start':
            solverRunning = solverRunning + 1; thinking = false; break;
          case 'solver.completed':
          case 'solver.cancelled':
            solverRunning = Math.max(0, solverRunning - 1); break;
          case 'aggregate.start':
            aggregateRunning = true; thinking = false; break;
          case 'aggregate.completed':
            aggregateRunning = false; break;
          case 'agent.user_confirm':
            thinking = false; break;
          case 'agent.final_answer':
          case 'pipeline.completed':
          case 'agent.interrupted':
          case 'agent.error':
          case 'system.error':
            planRunning = false; aggregateRunning = false; solverRunning = 0; thinking = false; break;
          case 'agent.thinking':
            thinking = true; break;
        }
        const generating = !!(planRunning || aggregateRunning || (solverRunning > 0) || thinking);
        if (m.event === 'agent.session_created') {
          return { ...s, currentSessionId: m.session_id, messages: nextMessages, lastEventId, lastSeq, planRunning, aggregateRunning, solverRunning, thinking, generating };
        }
        return { ...s, messages: nextMessages, lastEventId, lastSeq, planRunning, aggregateRunning, solverRunning, thinking, generating };
      });
    });
    return () => {
      off();
      client.disconnect();
      clientRef.current = null;
    };
  }, [wsUrl, token, autoReconnect, showSystemLogs, onEvent]);

  const send = useCallback((payload: any) => {
    clientRef.current?.send(payload);
  }, []);

  const api = useMemo<Ctx>(() => ({
    state,
    client: clientRef.current,
    createSession: (content?: any) => send({ event: 'user.create_session', content }),
    sendUserMessage: (content: any) => {
      if (!state.currentSessionId) return;
      send({ event: 'user.message', session_id: state.currentSessionId, content });
    },
    sendResponse: (stepId: string, content: any) => {
      if (!state.currentSessionId) return;
      send({ event: 'user.response', session_id: state.currentSessionId, step_id: stepId, content });
    },
    cancel: () => state.currentSessionId && send({ event: 'user.cancel', session_id: state.currentSessionId }),
    solveTasks: (tasks: any[], extras?: { question?: string; plan_summary?: string }) => {
      if (!state.currentSessionId) return;
      const content: any = { tasks };
      if (extras?.question) content.question = extras.question;
      if (extras?.plan_summary) content.plan_summary = extras.plan_summary;
      send({ event: 'user.solve_tasks', session_id: state.currentSessionId, content });
    },
    cancelTask: (taskId: string | number) => state.currentSessionId && send({ event: 'user.cancel_task', session_id: state.currentSessionId, content: { task_id: taskId } }),
    restartTask: (taskId: string | number) => state.currentSessionId && send({ event: 'user.restart_task', session_id: state.currentSessionId, content: { task_id: taskId } }),
    cancelPlan: () => state.currentSessionId && send({ event: 'user.cancel_plan', session_id: state.currentSessionId }),
    replan: (question?: string) => state.currentSessionId && send({ event: 'user.replan', session_id: state.currentSessionId, content: question ? { question } : undefined }),
    requestState: () => state.currentSessionId && send({ event: 'user.request_state', session_id: state.currentSessionId }),
    reconnectWithState: (signedState: any, last?: { last_event_id?: string; last_seq?: number }) =>
      send({ event: 'user.reconnect_with_state', signed_state: signedState, ...(last || {}) }),
  }), [send, state]);

  return <MyAgentCtx.Provider value={api}>{children}</MyAgentCtx.Provider>;
}

export function useMyAgent() {
  const ctx = useContext(MyAgentCtx);
  if (!ctx) throw new Error('useMyAgent must be used within MyAgentProvider');
  return ctx;
}
