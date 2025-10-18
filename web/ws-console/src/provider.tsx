import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { AgentConsoleState, ConfirmMessage, MyAgentProviderProps, WebSocketMessage } from './types';
import { AgentWSClient } from './ws-client';
import { DEFAULT_SESSION_ID, useSessionStore } from './session-store';

interface Ctx {
  state: AgentConsoleState;
  client: AgentWSClient | null;
  // Commands
  injectMessage: (message: WebSocketMessage, opts?: { sessionId?: string }) => void;
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
  selectSession: (sessionId: string) => void;
}

const MyAgentCtx = createContext<Ctx | null>(null);

export function MyAgentProvider(props: MyAgentProviderProps) {
  const { wsUrl, token, autoReconnect = true, showSystemLogs = false, onEvent, sessionId, children } = props;
  const [state, setState] = useState<AgentConsoleState>({
    connection: 'disconnected',
    messages: [],
    availableSessions: [],
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
    const client = new AgentWSClient({
      url: wsUrl,
      token,
      autoReconnect,
      onOpen: () => setState((s) => ({ ...s, connection: 'connected', error: null })),
      onClose: () => setState((s) => ({ ...s, connection: 'disconnected' })),
      onError: (err) => setState((s) => ({ ...s, connection: 'error', error: String(err) })),
    });
    clientRef.current = client;
    setState((s) => ({ ...s, connection: 'connecting' }));
    client.connect();

    const appendMessage = (message: WebSocketMessage) => {
      if (!showSystemLogs && String(message.event || '').startsWith('system.')) return;
      const store = useSessionStore.getState();
      const targetSessionId = message.session_id ?? store.currentSessionId;
      store.addMessage(targetSessionId, message);
    };

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

      appendMessage(m);

      setState((s) => {
        const lastEventId = typeof m.event_id === 'string' ? m.event_id : s.lastEventId ?? null;
        const lastSeq = typeof (m as any).seq === 'number' ? ((m as any).seq as number) : s.lastSeq ?? 0;
        // runtime counters
        let planRunning = !!s.planRunning;
        let aggregateRunning = !!s.aggregateRunning;
        let solverRunning = Math.max(0, s.solverRunning || 0);
        let thinking = !!s.thinking;
        let pendingConfirm: ConfirmMessage | null = s.pendingConfirm ?? null;
        const ev = String(m.event || '');
        switch (ev) {
          case 'plan.start':
            planRunning = true;
            thinking = false;
            break;
          case 'plan.completed':
          case 'plan.cancelled':
            planRunning = false;
            thinking = false;
            break;
          case 'solver.start':
            solverRunning = solverRunning + 1;
            thinking = false;
            break;
          case 'solver.completed':
          case 'solver.cancelled':
            solverRunning = Math.max(0, solverRunning - 1);
            break;
          case 'aggregate.start':
            aggregateRunning = true;
            thinking = false;
            break;
          case 'aggregate.completed':
            aggregateRunning = false;
            break;
          case 'agent.user_confirm':
            thinking = false;
            pendingConfirm = m as ConfirmMessage;
            break;
          case 'agent.final_answer':
          case 'pipeline.completed':
          case 'agent.interrupted':
          case 'agent.error':
          case 'system.error':
            planRunning = false;
            aggregateRunning = false;
            solverRunning = 0;
            thinking = false;
            break;
          case 'agent.thinking':
            thinking = true;
            break;
        }
        const generating = !!(planRunning || aggregateRunning || (solverRunning > 0) || thinking);
        return {
          ...s,
          lastEventId,
          lastSeq,
          planRunning,
          aggregateRunning,
          solverRunning,
          thinking,
          generating,
          pendingConfirm,
        };
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

  const sessions = useSessionStore((s) => s.sessions);
  const sessionOrder = useSessionStore((s) => s.sessionOrder);
  const storeViewSessionId = useSessionStore((s) => s.viewSessionId);
  const storeCurrentSessionId = useSessionStore((s) => s.currentSessionId);

  useEffect(() => {
    if (sessionId) {
      const store = useSessionStore.getState();
      store.setCurrentSession(sessionId);
      store.setViewSession(sessionId);
      setState((s) => (s.currentSessionId === sessionId ? s : { ...s, currentSessionId: sessionId }));
    } else {
      setState((s) => (typeof s.currentSessionId === 'undefined' ? s : { ...s, currentSessionId: undefined }));
    }
  }, [sessionId]);

  const effectiveViewSessionId = sessionId ?? storeViewSessionId ?? storeCurrentSessionId ?? state.currentSessionId;

  useEffect(() => {
    if (!effectiveViewSessionId && sessionOrder.length > 0) {
      const first = sessionOrder.find((id) => id !== DEFAULT_SESSION_ID);
      if (first) {
        useSessionStore.getState().setViewSession(first);
      }
    }
  }, [effectiveViewSessionId, sessionOrder]);

  const messages = useMemo(() => {
    if (!effectiveViewSessionId) return [] as WebSocketMessage[];
    return sessions[effectiveViewSessionId]?.messages ?? [];
  }, [sessions, effectiveViewSessionId]);

  const availableSessions = useMemo(
    () =>
      sessionOrder
        .filter((id) => id !== DEFAULT_SESSION_ID)
        .map((id) => ({
          sessionId: id,
          updatedAt: sessions[id]?.updatedAt,
          messageCount: sessions[id]?.messages.length ?? 0,
        })),
    [sessionOrder, sessions],
  );

  const derivedState = useMemo<AgentConsoleState>(() => ({
    ...state,
    currentSessionId: sessionId ?? state.currentSessionId,
    messages,
    availableSessions,
    viewSessionId: effectiveViewSessionId,
  }), [state, messages, availableSessions, effectiveViewSessionId, sessionId]);

  const api = useMemo<Ctx>(() => ({
    state: derivedState,
    client: clientRef.current,
    injectMessage: (message: WebSocketMessage, opts?: { sessionId?: string }) => {
      try {
        const now = new Date().toISOString();
        const resolvedSessionId = opts?.sessionId ?? (sessionId ?? derivedState.currentSessionId);
        const msg: WebSocketMessage = {
          event_id: message.event_id ?? `mock.${Date.now()}.${Math.random().toString(16).slice(2, 8)}`,
          ...message,
          session_id: message.session_id ?? resolvedSessionId,
          timestamp: message.timestamp ?? now,
        };
        useSessionStore.getState().addMessage(resolvedSessionId, msg);
      } catch (e) {
        console.error('[injectMessage] failed', e);
      }
    },
    createSession: (content?: any) => send({ event: 'user.create_session', content }),
    sendUserMessage: (content: any) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      const now = new Date().toISOString();
      useSessionStore.getState().addMessage(resolvedSessionId, {
        event: 'user.message',
        timestamp: now,
        session_id: resolvedSessionId,
        content,
        event_id: `user.message.local.${resolvedSessionId}.${Date.now()}.${Math.random().toString(16).slice(2, 8)}`,
        metadata: { local: true },
      });
      send({ event: 'user.message', session_id: resolvedSessionId, content });
    },
    sendResponse: (stepId: string, content: any) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: 'user.response', session_id: resolvedSessionId, step_id: stepId, content });
    },
    cancel: () => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: 'user.cancel', session_id: resolvedSessionId });
    },
    solveTasks: (tasks: any[], extras?: { question?: string; plan_summary?: string }) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      const content: any = { tasks };
      if (extras?.question) content.question = extras.question;
      if (extras?.plan_summary) content.plan_summary = extras.plan_summary;
      send({ event: 'user.solve_tasks', session_id: resolvedSessionId, content });
    },
    cancelTask: (taskId: string | number) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: 'user.cancel_task', session_id: resolvedSessionId, content: { task_id: taskId } });
    },
    restartTask: (taskId: string | number) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: 'user.restart_task', session_id: resolvedSessionId, content: { task_id: taskId } });
    },
    cancelPlan: () => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: 'user.cancel_plan', session_id: resolvedSessionId });
    },
    replan: (question?: string) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: 'user.replan', session_id: resolvedSessionId, content: question ? { question } : undefined });
    },
    requestState: () => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: 'user.request_state', session_id: resolvedSessionId });
    },
    reconnectWithState: (signedState: any, last?: { last_event_id?: string; last_seq?: number }) =>
      send({ event: 'user.reconnect_with_state', signed_state: signedState, ...(last || {}) }),
    selectSession: (sessionId: string) => {
      useSessionStore.getState().setViewSession(sessionId);
    },
  }), [send, derivedState]);

  return <MyAgentCtx.Provider value={api}>{children}</MyAgentCtx.Provider>;
}

export function useMyAgent() {
  const ctx = useContext(MyAgentCtx);
  if (!ctx) throw new Error('useMyAgent must be used within MyAgentProvider');
  return ctx;
}
