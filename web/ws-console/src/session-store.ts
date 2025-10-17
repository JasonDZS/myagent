import { useSyncExternalStore } from 'react';
import { createStore, StateCreator } from 'zustand/vanilla';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { WebSocketMessage } from './types';

export const DEFAULT_SESSION_ID = '__default__';

export interface CachedSession {
  sessionId: string;
  messages: WebSocketMessage[];
  createdAt: string;
  updatedAt: string;
  meta?: {
    title?: string;
  };
}

interface SessionStoreState {
  sessions: Record<string, CachedSession>;
  sessionOrder: string[];
  currentSessionId?: string;
  viewSessionId?: string;
  ensureSession: (sessionId?: string) => string;
  setCurrentSession: (sessionId?: string) => void;
  setViewSession: (sessionId?: string) => void;
  addMessage: (sessionId: string | undefined, message: WebSocketMessage) => void;
  addMessages: (sessionId: string | undefined, messages: WebSocketMessage[]) => void;
  clear: () => void;
  dropSession: (sessionId: string) => void;
}

const createSessionRecord = (sessionId: string, message?: WebSocketMessage): CachedSession => {
  const timestamp = message?.timestamp ?? new Date().toISOString();
  return {
    sessionId,
    messages: message ? [message] : [],
    createdAt: timestamp,
    updatedAt: timestamp,
  };
};

const baseStore: StateCreator<SessionStoreState> = (set, get) => ({
  sessions: {},
  sessionOrder: [],
  currentSessionId: undefined,
  viewSessionId: undefined,
  ensureSession: (sessionId) => {
    const id = sessionId || get().currentSessionId || DEFAULT_SESSION_ID;
    const state = get();
    if (!state.sessions[id]) {
      const sessions = { ...state.sessions, [id]: createSessionRecord(id) };
      const order = state.sessionOrder.includes(id) ? state.sessionOrder : [...state.sessionOrder, id];
      set({ sessions, sessionOrder: order });
    }
    return id;
  },
  setCurrentSession: (sessionId) => {
    if (!sessionId) return;
    const id = get().ensureSession(sessionId);
    set((state) => ({
      currentSessionId: id,
      viewSessionId: state.viewSessionId ?? id,
      sessionOrder: state.sessionOrder.includes(id)
        ? state.sessionOrder
        : [...state.sessionOrder, id],
    }));
  },
  setViewSession: (sessionId) => {
    if (!sessionId) return;
    const id = get().ensureSession(sessionId);
    set({ viewSessionId: id });
  },
  addMessage: (sessionId, message) => {
    const id = get().ensureSession(sessionId);
    set((state) => {
      const prev = state.sessions[id] ?? createSessionRecord(id);
      const messages = prev.messages.slice();
      if (message.event_id) {
        const idx = messages.findIndex((m) => m.event_id === message.event_id);
        if (idx !== -1) {
          messages[idx] = message;
        } else {
          messages.push(message);
        }
      } else {
        messages.push(message);
      }
      const updated: CachedSession = {
        ...prev,
        messages,
        updatedAt: message.timestamp ?? new Date().toISOString(),
      };
      const sessions = { ...state.sessions, [id]: updated };
      const order = state.sessionOrder.filter((sid) => sid !== id);
      order.unshift(id);
      return {
        sessions,
        sessionOrder: order,
      };
    });
  },
  addMessages: (sessionId, messages) => {
    messages.forEach((msg) => get().addMessage(sessionId, msg));
  },
  clear: () => {
    set({
      sessions: {},
      sessionOrder: [],
      currentSessionId: undefined,
      viewSessionId: undefined,
    });
  },
  dropSession: (sessionId) => {
    set((state) => {
      if (!state.sessions[sessionId]) return state;
      const { [sessionId]: _removed, ...rest } = state.sessions;
      const order = state.sessionOrder.filter((id) => id !== sessionId);
      const current =
        state.currentSessionId === sessionId ? order[0] : state.currentSessionId;
      const view =
        state.viewSessionId === sessionId ? current ?? order[0] : state.viewSessionId;
      return {
        sessions: rest,
        sessionOrder: order,
        currentSessionId: current,
        viewSessionId: view,
      };
    });
  },
});

const storage =
  typeof window !== 'undefined'
    ? createJSONStorage<SessionStoreState>(() => localStorage)
    : undefined;

const storeInitializer = storage
  ? persist(baseStore, {
      name: 'myagent-session-cache',
      storage,
      partialize: (state) => ({
        sessions: state.sessions,
        sessionOrder: state.sessionOrder,
        currentSessionId: state.currentSessionId,
        viewSessionId: state.viewSessionId,
      }),
    })
  : baseStore;

const sessionStore = createStore<SessionStoreState>()(storeInitializer);

type Selector<T> = (state: SessionStoreState) => T;
type UseSessionStore = {
  (): SessionStoreState;
  <T>(selector: Selector<T>): T;
  getState: typeof sessionStore.getState;
  setState: typeof sessionStore.setState;
  subscribe: typeof sessionStore.subscribe;
  getInitialState: typeof sessionStore.getInitialState;
};

const identity = <T>(value: T) => value;

export const useSessionStore: UseSessionStore = ((selector?: Selector<any>) => {
  const sel = (selector ?? identity) as Selector<any>;
  return useSyncExternalStore(
    sessionStore.subscribe,
    () => sel(sessionStore.getState()),
    () => sel(sessionStore.getInitialState()),
  );
}) as UseSessionStore;

useSessionStore.getState = sessionStore.getState;
useSessionStore.setState = sessionStore.setState;
useSessionStore.subscribe = sessionStore.subscribe;
useSessionStore.getInitialState = sessionStore.getInitialState;
