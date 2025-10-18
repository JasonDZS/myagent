// src/provider.tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

// src/ws-client.ts
var AgentWSClient = class {
  constructor(opts) {
    this.ws = null;
    this.listeners = /* @__PURE__ */ new Set();
    this.reconnectTimer = null;
    this.lastEventId = null;
    this.lastSeq = 0;
    this.ackTimer = null;
    this.connected = false;
    this.opts = { autoReconnect: true, ackIntervalMs: 200, ...opts };
  }
  isOpen() {
    return this.connected && !!this.ws && this.ws.readyState === WebSocket.OPEN;
  }
  getLastEvent() {
    return { lastEventId: this.lastEventId, lastSeq: this.lastSeq };
  }
  onMessage(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }
  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    try {
      const url = this.buildUrlWithToken();
      this.ws = new WebSocket(url);
      this.connected = false;
      this.ws.onopen = () => {
        this.connected = true;
        this.startAckLoop();
        this.opts.onOpen?.();
      };
      this.ws.onclose = (ev) => {
        this.connected = false;
        this.stopAckLoop();
        this.opts.onClose?.(ev);
        if (this.opts.autoReconnect) this.scheduleReconnect();
      };
      this.ws.onerror = (err) => {
        this.opts.onError?.(err);
      };
      this.ws.onmessage = (e) => {
        try {
          const m = JSON.parse(e.data);
          if (typeof m.event_id === "string") this.lastEventId = m.event_id;
          if (typeof m.seq === "number") this.lastSeq = m.seq;
          this.listeners.forEach((fn) => fn(m));
        } catch (err) {
          console.warn("Invalid WS message", err);
        }
      };
    } catch (err) {
      this.opts.onError?.(err);
      if (this.opts.autoReconnect) this.scheduleReconnect();
    }
  }
  disconnect() {
    this.opts.autoReconnect = false;
    this.stopAckLoop();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    try {
      this.ws?.close();
    } catch {
    }
    this.ws = null;
    this.connected = false;
  }
  scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 1e3);
  }
  startAckLoop() {
    this.stopAckLoop();
    const interval = this.opts.ackIntervalMs ?? 200;
    this.ackTimer = setInterval(() => {
      if (!this.isOpen()) return;
      const content = this.lastEventId ? { last_event_id: this.lastEventId } : { last_seq: this.lastSeq };
      this.send({ event: "user.ack", content });
    }, interval);
  }
  stopAckLoop() {
    if (this.ackTimer) clearInterval(this.ackTimer);
    this.ackTimer = null;
  }
  buildUrlWithToken() {
    if (!this.opts.token) return this.opts.url;
    try {
      const u = new URL(this.opts.url);
      u.searchParams.set("token", this.opts.token);
      return u.toString();
    } catch {
      const sep = this.opts.url.includes("?") ? "&" : "?";
      return `${this.opts.url}${sep}token=${encodeURIComponent(this.opts.token)}`;
    }
  }
  send(payload) {
    if (!this.ws) return;
    try {
      this.ws.send(JSON.stringify({ ...payload, timestamp: (/* @__PURE__ */ new Date()).toISOString() }));
    } catch (err) {
      this.opts.onError?.(err);
    }
  }
};

// src/session-store.ts
import { useSyncExternalStore } from "react";
import { createStore } from "zustand/vanilla";
import { createJSONStorage, persist } from "zustand/middleware";
var DEFAULT_SESSION_ID = "__default__";
var createSessionRecord = (sessionId, message) => {
  const timestamp = message?.timestamp ?? (/* @__PURE__ */ new Date()).toISOString();
  return {
    sessionId,
    messages: message ? [message] : [],
    createdAt: timestamp,
    updatedAt: timestamp
  };
};
var baseStore = (set, get) => ({
  sessions: {},
  sessionOrder: [],
  currentSessionId: void 0,
  viewSessionId: void 0,
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
      sessionOrder: state.sessionOrder.includes(id) ? state.sessionOrder : [...state.sessionOrder, id]
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
      const updated = {
        ...prev,
        messages,
        updatedAt: message.timestamp ?? (/* @__PURE__ */ new Date()).toISOString()
      };
      const sessions = { ...state.sessions, [id]: updated };
      const order = state.sessionOrder.filter((sid) => sid !== id);
      order.unshift(id);
      return {
        sessions,
        sessionOrder: order
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
      currentSessionId: void 0,
      viewSessionId: void 0
    });
  },
  dropSession: (sessionId) => {
    set((state) => {
      if (!state.sessions[sessionId]) return state;
      const { [sessionId]: _removed, ...rest } = state.sessions;
      const order = state.sessionOrder.filter((id) => id !== sessionId);
      const current = state.currentSessionId === sessionId ? order[0] : state.currentSessionId;
      const view = state.viewSessionId === sessionId ? current ?? order[0] : state.viewSessionId;
      return {
        sessions: rest,
        sessionOrder: order,
        currentSessionId: current,
        viewSessionId: view
      };
    });
  }
});
var storage = typeof window !== "undefined" ? createJSONStorage(() => localStorage) : void 0;
var storeInitializer = storage ? persist(baseStore, {
  name: "myagent-session-cache",
  storage,
  partialize: (state) => ({
    sessions: state.sessions,
    sessionOrder: state.sessionOrder,
    currentSessionId: state.currentSessionId,
    viewSessionId: state.viewSessionId
  })
}) : baseStore;
var sessionStore = createStore()(storeInitializer);
var identity = (value) => value;
var useSessionStore = ((selector) => {
  const sel = selector ?? identity;
  return useSyncExternalStore(
    sessionStore.subscribe,
    () => sel(sessionStore.getState()),
    () => sel(sessionStore.getInitialState())
  );
});
useSessionStore.getState = sessionStore.getState;
useSessionStore.setState = sessionStore.setState;
useSessionStore.subscribe = sessionStore.subscribe;
useSessionStore.getInitialState = sessionStore.getInitialState;

// src/provider.tsx
import { jsx } from "react/jsx-runtime";
var MyAgentCtx = createContext(null);
function MyAgentProvider(props) {
  const { wsUrl, token, autoReconnect = true, showSystemLogs = false, onEvent, sessionId, children } = props;
  const [state, setState] = useState({
    connection: "disconnected",
    messages: [],
    availableSessions: [],
    lastEventId: null,
    lastSeq: 0,
    pendingConfirm: null,
    generating: false,
    planRunning: false,
    aggregateRunning: false,
    solverRunning: 0,
    thinking: false
  });
  const clientRef = useRef(null);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const client = new AgentWSClient({
      url: wsUrl,
      token,
      autoReconnect,
      onOpen: () => setState((s) => ({ ...s, connection: "connected", error: null })),
      onClose: () => setState((s) => ({ ...s, connection: "disconnected" })),
      onError: (err) => setState((s) => ({ ...s, connection: "error", error: String(err) }))
    });
    clientRef.current = client;
    setState((s) => ({ ...s, connection: "connecting" }));
    client.connect();
    const appendMessage = (message) => {
      if (!showSystemLogs && String(message.event || "").startsWith("system.")) return;
      const store = useSessionStore.getState();
      const targetSessionId = message.session_id ?? store.currentSessionId;
      store.addMessage(targetSessionId, message);
    };
    const off = client.onMessage((m) => {
      onEvent?.(m);
      try {
        if (m.event === "agent.state_exported") {
          const sid = m.session_id || "unknown";
          const signed = m.metadata?.signed_state;
          if (signed && typeof localStorage !== "undefined") {
            localStorage.setItem(`ma_state_${sid}`, JSON.stringify(signed));
            localStorage.setItem(`ma_state_latest`, JSON.stringify(signed));
          }
        }
      } catch {
      }
      appendMessage(m);
      setState((s) => {
        const lastEventId = typeof m.event_id === "string" ? m.event_id : s.lastEventId ?? null;
        const lastSeq = typeof m.seq === "number" ? m.seq : s.lastSeq ?? 0;
        let planRunning = !!s.planRunning;
        let aggregateRunning = !!s.aggregateRunning;
        let solverRunning = Math.max(0, s.solverRunning || 0);
        let thinking = !!s.thinking;
        let pendingConfirm = s.pendingConfirm ?? null;
        const ev = String(m.event || "");
        switch (ev) {
          case "plan.start":
            planRunning = true;
            thinking = false;
            break;
          case "plan.completed":
          case "plan.cancelled":
            planRunning = false;
            thinking = false;
            break;
          case "solver.start":
            solverRunning = solverRunning + 1;
            thinking = false;
            break;
          case "solver.completed":
          case "solver.cancelled":
            solverRunning = Math.max(0, solverRunning - 1);
            break;
          case "aggregate.start":
            aggregateRunning = true;
            thinking = false;
            break;
          case "aggregate.completed":
            aggregateRunning = false;
            break;
          case "agent.user_confirm":
            thinking = false;
            pendingConfirm = m;
            break;
          case "agent.final_answer":
          case "pipeline.completed":
          case "agent.interrupted":
          case "agent.error":
          case "system.error":
            planRunning = false;
            aggregateRunning = false;
            solverRunning = 0;
            thinking = false;
            break;
          case "agent.thinking":
            thinking = true;
            break;
        }
        const generating = !!(planRunning || aggregateRunning || solverRunning > 0 || thinking);
        return {
          ...s,
          lastEventId,
          lastSeq,
          planRunning,
          aggregateRunning,
          solverRunning,
          thinking,
          generating,
          pendingConfirm
        };
      });
    });
    return () => {
      off();
      client.disconnect();
      clientRef.current = null;
    };
  }, [wsUrl, token, autoReconnect, showSystemLogs, onEvent]);
  const send = useCallback((payload) => {
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
      setState((s) => s.currentSessionId === sessionId ? s : { ...s, currentSessionId: sessionId });
    } else {
      setState((s) => typeof s.currentSessionId === "undefined" ? s : { ...s, currentSessionId: void 0 });
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
    if (!effectiveViewSessionId) return [];
    return sessions[effectiveViewSessionId]?.messages ?? [];
  }, [sessions, effectiveViewSessionId]);
  const availableSessions = useMemo(
    () => sessionOrder.filter((id) => id !== DEFAULT_SESSION_ID).map((id) => ({
      sessionId: id,
      updatedAt: sessions[id]?.updatedAt,
      messageCount: sessions[id]?.messages.length ?? 0
    })),
    [sessionOrder, sessions]
  );
  const derivedState = useMemo(() => ({
    ...state,
    currentSessionId: sessionId ?? state.currentSessionId,
    messages,
    availableSessions,
    viewSessionId: effectiveViewSessionId
  }), [state, messages, availableSessions, effectiveViewSessionId, sessionId]);
  const api = useMemo(() => ({
    state: derivedState,
    client: clientRef.current,
    injectMessage: (message, opts) => {
      try {
        const now = (/* @__PURE__ */ new Date()).toISOString();
        const resolvedSessionId = opts?.sessionId ?? (sessionId ?? derivedState.currentSessionId);
        const msg = {
          event_id: message.event_id ?? `mock.${Date.now()}.${Math.random().toString(16).slice(2, 8)}`,
          ...message,
          session_id: message.session_id ?? resolvedSessionId,
          timestamp: message.timestamp ?? now
        };
        useSessionStore.getState().addMessage(resolvedSessionId, msg);
      } catch (e) {
        console.error("[injectMessage] failed", e);
      }
    },
    createSession: (content) => send({ event: "user.create_session", content }),
    sendUserMessage: (content) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      const now = (/* @__PURE__ */ new Date()).toISOString();
      useSessionStore.getState().addMessage(resolvedSessionId, {
        event: "user.message",
        timestamp: now,
        session_id: resolvedSessionId,
        content,
        event_id: `user.message.local.${resolvedSessionId}.${Date.now()}.${Math.random().toString(16).slice(2, 8)}`,
        metadata: { local: true }
      });
      send({ event: "user.message", session_id: resolvedSessionId, content });
    },
    sendResponse: (stepId, content) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: "user.response", session_id: resolvedSessionId, step_id: stepId, content });
    },
    cancel: () => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: "user.cancel", session_id: resolvedSessionId });
    },
    solveTasks: (tasks, extras) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      const content = { tasks };
      if (extras?.question) content.question = extras.question;
      if (extras?.plan_summary) content.plan_summary = extras.plan_summary;
      send({ event: "user.solve_tasks", session_id: resolvedSessionId, content });
    },
    cancelTask: (taskId) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: "user.cancel_task", session_id: resolvedSessionId, content: { task_id: taskId } });
    },
    restartTask: (taskId) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: "user.restart_task", session_id: resolvedSessionId, content: { task_id: taskId } });
    },
    cancelPlan: () => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: "user.cancel_plan", session_id: resolvedSessionId });
    },
    replan: (question) => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: "user.replan", session_id: resolvedSessionId, content: question ? { question } : void 0 });
    },
    requestState: () => {
      const resolvedSessionId = sessionId ?? derivedState.currentSessionId;
      if (!resolvedSessionId) return;
      send({ event: "user.request_state", session_id: resolvedSessionId });
    },
    reconnectWithState: (signedState, last) => send({ event: "user.reconnect_with_state", signed_state: signedState, ...last || {} }),
    selectSession: (sessionId2) => {
      useSessionStore.getState().setViewSession(sessionId2);
    }
  }), [send, derivedState]);
  return /* @__PURE__ */ jsx(MyAgentCtx.Provider, { value: api, children });
}
function useMyAgent() {
  const ctx = useContext(MyAgentCtx);
  if (!ctx) throw new Error("useMyAgent must be used within MyAgentProvider");
  return ctx;
}

// src/components/MessageList.tsx
import { useEffect as useEffect3, useRef as useRef2 } from "react";

// src/components/MessageItem.tsx
import { useEffect as useEffect2, useMemo as useMemo2, useState as useState2 } from "react";
import { User, Bot, Settings, ListTodo, Wrench, Puzzle, GitMerge, Cpu, Hash, LogIn, LogOut } from "lucide-react";
import { Fragment, jsx as jsx2, jsxs } from "react/jsx-runtime";
function stringifyContent(content) {
  if (content == null) return "";
  if (typeof content === "string") return content;
  try {
    return JSON.stringify(content, null, 2);
  } catch {
    return String(content);
  }
}
function friendlyFromClientFallback(m) {
  const ev = String(m.event || "");
  const c = m.content;
  const md = m.metadata || {};
  try {
    if (ev === "system.connected") return "\u5DF2\u8FDE\u63A5\u5230\u670D\u52A1\u5668";
    if (ev === "system.error") return typeof c === "string" ? `\u7CFB\u7EDF\u9519\u8BEF\uFF1A${c}` : "\u7CFB\u7EDF\u9519\u8BEF";
    if (ev === "agent.session_created") return "\u4F1A\u8BDD\u521B\u5EFA\u6210\u529F";
    if (ev === "agent.thinking") return "\u6B63\u5728\u601D\u8003\u2026";
    if (ev === "agent.partial_answer") return typeof c === "string" ? c : "\u751F\u6210\u4E2D\u2026";
    if (ev === "agent.final_answer") return typeof c === "string" ? c : "\u5DF2\u751F\u6210\u7B54\u6848";
    if (ev === "agent.user_confirm") {
      const scope = md?.scope || "plan";
      const tasks = Array.isArray(md?.tasks) ? md.tasks : void 0;
      const count = tasks ? tasks.length : void 0;
      const sum = typeof md?.plan_summary === "string" ? md.plan_summary : void 0;
      return scope === "plan" ? `\u8BF7\u786E\u8BA4\u89C4\u5212${count != null ? `\uFF08${count} \u4E2A\u4EFB\u52A1\uFF09` : ""}${sum ? `\uFF1A${sum}` : ""}` : "\u8BF7\u786E\u8BA4\u64CD\u4F5C";
    }
    if (ev === "plan.start") return typeof c?.question === "string" ? `\u5F00\u59CB\u89C4\u5212\uFF1A${c.question}` : "\u5F00\u59CB\u89C4\u5212";
    if (ev === "plan.completed") {
      const tasks = Array.isArray(c?.tasks) ? c.tasks : void 0;
      const count = tasks ? tasks.length : void 0;
      const sum = typeof c?.plan_summary === "string" ? c.plan_summary : void 0;
      return `\u89C4\u5212\u5B8C\u6210${count != null ? `\uFF08${count} \u4E2A\u4EFB\u52A1\uFF09` : ""}${sum ? `\uFF1A${sum}` : ""}`;
    }
    if (ev === "solver.start") {
      const task = c?.task;
      const title = typeof task?.title === "string" ? task.title : typeof task?.name === "string" ? task.name : void 0;
      return title ? `\u5F00\u59CB\u6C42\u89E3\uFF1A${title}` : "\u5F00\u59CB\u6C42\u89E3";
    }
    if (ev === "solver.completed") {
      const task = c?.task;
      const title = typeof task?.title === "string" ? task.title : typeof task?.name === "string" ? task.name : void 0;
      return title ? `\u6C42\u89E3\u5B8C\u6210\uFF1A${title}` : "\u6C42\u89E3\u5B8C\u6210";
    }
    if (ev === "aggregate.start") return "\u5F00\u59CB\u805A\u5408";
    if (ev === "aggregate.completed") return "\u805A\u5408\u5B8C\u6210";
    if (ev === "pipeline.completed") return "\u6D41\u6C34\u7EBF\u5B8C\u6210";
  } catch {
  }
  return void 0;
}
function MessageItem({ m, onConfirm, onDecline }) {
  const event = String(m.event || "");
  let role = "system";
  if (event.startsWith("agent.") || event.startsWith("plan.") || event.startsWith("solver.") || event.startsWith("aggregate.") || event === "pipeline.completed") role = "agent";
  if (event.startsWith("user.")) role = "user";
  const cls = `ma-item ma-${role}`;
  const label = event.replace(/^.*\./, "");
  const preferred = typeof m.show_content === "string" ? m.show_content : friendlyFromClientFallback(m);
  const body = stringifyContent(preferred ?? m.content);
  const ts = m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : "";
  const stats = useMemo2(() => computeStats(m), [m]);
  const isConfirm = event === "agent.user_confirm";
  const [collapsed, setCollapsed] = useState2(() => !isConfirm);
  const category = getCategory(event);
  const Icon = getIcon(category);
  const preview = useMemo2(() => {
    const s = body.replace(/\s+/g, " ").trim();
    return s.length > 140 ? s.slice(0, 140) + "\u2026" : s;
  }, [body]);
  const confirm = isConfirm ? m : void 0;
  const tasks = useMemo2(() => {
    const t = confirm?.metadata?.tasks;
    return Array.isArray(t) ? t : null;
  }, [confirm]);
  const [json, setJson] = useState2("");
  const [err, setErr] = useState2(null);
  const [sent, setSent] = useState2(false);
  const [selection, setSelection] = useState2(null);
  const [editMode, setEditMode] = useState2("form");
  const [formTasks, setFormTasks] = useState2([]);
  useEffect2(() => {
    if (isConfirm) {
      setJson(tasks ? JSON.stringify(tasks, null, 2) : "");
      setErr(null);
      setSent(false);
      setSelection(null);
      setCollapsed(false);
      setEditMode("form");
      try {
        setFormTasks(Array.isArray(tasks) ? tasks.map((t) => t && typeof t === "object" ? { ...t } : t) : []);
      } catch {
        setFormTasks([]);
      }
    }
  }, [isConfirm, confirm?.step_id]);
  const scope = confirm?.metadata?.scope || "plan";
  const title = scope === "plan" ? "\u786E\u8BA4\u89C4\u5212\u4EFB\u52A1" : "\u786E\u8BA4\u64CD\u4F5C";
  const planSummary = confirm?.metadata?.plan_summary;
  const hasEditable = Boolean(tasks);
  if (isConfirm) {
    const handleConfirm = () => {
      if (sent) return;
      if (hasEditable) {
        try {
          let finalTasks = [];
          if (editMode === "json") {
            const parsed = JSON.parse(json || "[]");
            if (!Array.isArray(parsed)) throw new Error("JSON \u5FC5\u987B\u4E3A\u6570\u7EC4");
            finalTasks = parsed;
          } else {
            finalTasks = Array.isArray(formTasks) ? formTasks : [];
          }
          onConfirm?.(confirm, { confirmed: true, tasks: finalTasks });
          setSelection("confirmed");
          setSent(true);
          setCollapsed(true);
        } catch (e) {
          setErr(String(e?.message || e));
          return;
        }
      } else {
        onConfirm?.(confirm, { confirmed: true });
        setSelection("confirmed");
        setSent(true);
        setCollapsed(true);
      }
    };
    const handleDecline = () => {
      if (sent) return;
      onDecline?.(confirm, { confirmed: false });
      setSelection("declined");
      setSent(true);
      setCollapsed(true);
    };
    return /* @__PURE__ */ jsx2("div", { className: cls, children: /* @__PURE__ */ jsxs("div", { className: "ma-msg", children: [
      /* @__PURE__ */ jsxs("div", { className: "ma-msg-head", children: [
        /* @__PURE__ */ jsxs("div", { className: "ma-left", children: [
          /* @__PURE__ */ jsx2("span", { className: `ma-icon ${category}`, children: /* @__PURE__ */ jsx2(Icon, { size: 16 }) }),
          /* @__PURE__ */ jsxs("div", { className: "ma-muted", children: [
            "[",
            label,
            "] ",
            ts
          ] })
        ] }),
        /* @__PURE__ */ jsxs("div", { className: "ma-right", children: [
          stats?.show && /* @__PURE__ */ jsxs("div", { className: "ma-stats ma-stats-head", children: [
            stats.model && /* @__PURE__ */ jsxs("span", { className: "ma-chip", title: "\u6A21\u578B/Agent", children: [
              /* @__PURE__ */ jsx2(Cpu, { size: 12 }),
              /* @__PURE__ */ jsx2("span", { className: "ma-chip-text", children: stats.model })
            ] }),
            /* @__PURE__ */ jsxs("span", { className: "ma-chip", title: "\u8C03\u7528\u6B21\u6570", children: [
              /* @__PURE__ */ jsx2(Hash, { size: 12 }),
              /* @__PURE__ */ jsx2("span", { className: "ma-chip-text", children: stats.calls })
            ] }),
            /* @__PURE__ */ jsxs("span", { className: "ma-chip", title: "\u8F93\u5165 tokens", children: [
              /* @__PURE__ */ jsx2(LogIn, { size: 12 }),
              /* @__PURE__ */ jsx2("span", { className: "ma-chip-text", children: stats.inputTokens })
            ] }),
            /* @__PURE__ */ jsxs("span", { className: "ma-chip", title: "\u8F93\u51FA tokens", children: [
              /* @__PURE__ */ jsx2(LogOut, { size: 12 }),
              /* @__PURE__ */ jsx2("span", { className: "ma-chip-text", children: stats.outputTokens })
            ] })
          ] }),
          /* @__PURE__ */ jsx2("button", { className: "ma-linkbtn", onClick: () => setCollapsed((v) => !v), children: collapsed ? "\u5C55\u5F00" : "\u6298\u53E0" })
        ] })
      ] }),
      !collapsed && /* @__PURE__ */ jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }, children: [
        /* @__PURE__ */ jsx2("strong", { children: title }),
        /* @__PURE__ */ jsxs("span", { className: "ma-muted", children: [
          "step: ",
          confirm?.step_id
        ] })
      ] }),
      !collapsed && planSummary && /* @__PURE__ */ jsx2("div", { className: "ma-muted", style: { marginTop: 4 }, children: planSummary }),
      !collapsed && hasEditable ? /* @__PURE__ */ jsxs(Fragment, { children: [
        /* @__PURE__ */ jsxs("div", { className: "ma-toolbar", children: [
          /* @__PURE__ */ jsxs("div", { className: "ma-muted", children: [
            "\u5171\u6709 ",
            formTasks.length,
            " \u4E2A\u4EFB\u52A1"
          ] }),
          /* @__PURE__ */ jsxs("div", { style: { display: "flex", gap: 8 }, children: [
            /* @__PURE__ */ jsx2("button", { className: "ma-linkbtn", onClick: () => {
              setEditMode("form");
              setJson(JSON.stringify(formTasks, null, 2));
            }, children: "\u8868\u5355\u7F16\u8F91" }),
            /* @__PURE__ */ jsx2("button", { className: "ma-linkbtn", onClick: () => {
              setEditMode("json");
              setJson(JSON.stringify(formTasks, null, 2));
            }, children: "\u7F16\u8F91 JSON" })
          ] })
        ] }),
        editMode === "json" ? /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx2("div", { className: "ma-muted", style: { marginTop: 8 }, children: "\u7F16\u8F91 JSON \u4EE5\u4FEE\u6539\u4EFB\u52A1\uFF1A" }),
          /* @__PURE__ */ jsx2("textarea", { className: "ma-json", value: json, onChange: (e) => setJson(e.target.value) }),
          err && /* @__PURE__ */ jsx2("div", { style: { color: "#ef4444" }, children: err })
        ] }) : /* @__PURE__ */ jsx2("div", { className: "ma-tasklist", children: formTasks.map((t, idx) => /* @__PURE__ */ jsxs("div", { className: "ma-task", children: [
          /* @__PURE__ */ jsxs("div", { className: "ma-task-head", children: [
            "#",
            idx + 1,
            " ",
            t?.title || t?.name || `\u4EFB\u52A1 ${idx + 1}`
          ] }),
          /* @__PURE__ */ jsxs("div", { className: "ma-form", children: [
            /* @__PURE__ */ jsxs("div", { className: "ma-field", children: [
              /* @__PURE__ */ jsx2("label", { className: "ma-label", children: "\u6807\u9898\uFF08title\uFF09" }),
              /* @__PURE__ */ jsx2("input", { className: "ma-inputbox", value: t?.title || "", onChange: (e) => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, title: e.target.value } : x)) })
            ] }),
            /* @__PURE__ */ jsxs("div", { className: "ma-field", children: [
              /* @__PURE__ */ jsx2("label", { className: "ma-label", children: "\u76EE\u6807\uFF08objective\uFF09" }),
              /* @__PURE__ */ jsx2("textarea", { className: "ma-inputbox", value: t?.objective || "", onChange: (e) => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, objective: e.target.value } : x)) })
            ] }),
            /* @__PURE__ */ jsxs("div", { className: "ma-field", children: [
              /* @__PURE__ */ jsx2("label", { className: "ma-label", children: "\u5907\u6CE8\uFF08notes\uFF09" }),
              /* @__PURE__ */ jsx2("input", { className: "ma-inputbox", value: t?.notes || "", onChange: (e) => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, notes: e.target.value } : x)) })
            ] }),
            /* @__PURE__ */ jsxs("div", { className: "ma-field", children: [
              /* @__PURE__ */ jsx2("label", { className: "ma-label", children: "\u63D0\u793A\uFF08insights\uFF09" }),
              /* @__PURE__ */ jsxs("div", { className: "ma-form", children: [
                Array.isArray(t?.insights) && t.insights.length > 0 ? t.insights.map((it, j) => /* @__PURE__ */ jsxs("div", { className: "ma-inputrow", children: [
                  /* @__PURE__ */ jsx2("input", { className: "ma-inputbox", value: String(it), onChange: (e) => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, insights: x.insights.map((s, k) => k === j ? e.target.value : s) } : x)) }),
                  /* @__PURE__ */ jsx2("button", { className: "ma-mini", onClick: () => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, insights: x.insights.filter((_, k) => k !== j) } : x)), children: "\u5220\u9664" })
                ] }, j)) : /* @__PURE__ */ jsx2("div", { className: "ma-muted", children: "\u6682\u65E0" }),
                /* @__PURE__ */ jsx2("button", { className: "ma-mini", onClick: () => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, insights: Array.isArray(x.insights) ? [...x.insights, ""] : [""] } : x)), children: "\u65B0\u589E" })
              ] })
            ] })
          ] })
        ] }, idx)) })
      ] }) : !collapsed ? /* @__PURE__ */ jsx2("div", { className: "ma-muted", style: { marginTop: 8 }, children: "\u662F\u5426\u7EE7\u7EED\u6267\u884C\uFF1F" }) : /* @__PURE__ */ jsx2("div", { className: "ma-muted ma-preview", children: selection === "confirmed" ? "\u5DF2\u786E\u8BA4\u3002" : selection === "declined" ? "\u5DF2\u53D6\u6D88\u3002" : `\u9700\u8981\u786E\u8BA4\uFF08${title}\uFF09\u3002\u70B9\u51FB\u201C\u5C55\u5F00\u201D\u67E5\u770B\u8BE6\u7EC6\u3002` }),
      !collapsed && /* @__PURE__ */ jsxs("div", { className: "ma-row", style: { marginTop: 8 }, children: [
        /* @__PURE__ */ jsx2("button", { className: "ma-btn", disabled: sent, onClick: handleDecline, children: "\u53D6\u6D88" }),
        /* @__PURE__ */ jsx2("button", { className: "ma-btn", disabled: sent, onClick: handleConfirm, children: "\u786E\u8BA4" })
      ] })
    ] }) });
  }
  return /* @__PURE__ */ jsx2("div", { className: cls, children: /* @__PURE__ */ jsxs("div", { className: "ma-msg", children: [
    /* @__PURE__ */ jsxs("div", { className: "ma-msg-head", children: [
      /* @__PURE__ */ jsxs("div", { className: "ma-left", children: [
        /* @__PURE__ */ jsx2("span", { className: `ma-icon ${category}`, children: /* @__PURE__ */ jsx2(Icon, { size: 16 }) }),
        /* @__PURE__ */ jsxs("div", { className: "ma-muted", children: [
          "[",
          label,
          "] ",
          ts
        ] })
      ] }),
      /* @__PURE__ */ jsxs("div", { className: "ma-right", children: [
        stats?.show && /* @__PURE__ */ jsxs("div", { className: "ma-stats ma-stats-head", children: [
          stats.model && /* @__PURE__ */ jsxs("span", { className: "ma-chip", title: "\u6A21\u578B/Agent", children: [
            /* @__PURE__ */ jsx2(Cpu, { size: 12 }),
            /* @__PURE__ */ jsx2("span", { className: "ma-chip-text", children: stats.model })
          ] }),
          /* @__PURE__ */ jsxs("span", { className: "ma-chip", title: "\u8C03\u7528\u6B21\u6570", children: [
            /* @__PURE__ */ jsx2(Hash, { size: 12 }),
            /* @__PURE__ */ jsx2("span", { className: "ma-chip-text", children: stats.calls })
          ] }),
          /* @__PURE__ */ jsxs("span", { className: "ma-chip", title: "\u8F93\u5165 tokens", children: [
            /* @__PURE__ */ jsx2(LogIn, { size: 12 }),
            /* @__PURE__ */ jsx2("span", { className: "ma-chip-text", children: stats.inputTokens })
          ] }),
          /* @__PURE__ */ jsxs("span", { className: "ma-chip", title: "\u8F93\u51FA tokens", children: [
            /* @__PURE__ */ jsx2(LogOut, { size: 12 }),
            /* @__PURE__ */ jsx2("span", { className: "ma-chip-text", children: stats.outputTokens })
          ] })
        ] }),
        /* @__PURE__ */ jsx2("button", { className: "ma-linkbtn", onClick: () => setCollapsed((v) => !v), children: collapsed ? "\u5C55\u5F00" : "\u6298\u53E0" })
      ] })
    ] }),
    collapsed ? /* @__PURE__ */ jsx2("div", { className: "ma-muted ma-preview", children: preview }) : /* @__PURE__ */ jsx2("div", { children: body })
  ] }) });
}
function getCategory(event) {
  if (event.startsWith("user.")) return "user";
  if (event.startsWith("agent.")) return "agent";
  if (event.startsWith("plan.")) return "plan";
  if (event.startsWith("solver.")) return "solver";
  if (event.startsWith("aggregate.")) return "aggregate";
  if (event === "pipeline.completed" || event.startsWith("pipeline.")) return "pipeline";
  if (event.startsWith("system.")) return "system";
  return "system";
}
function getIcon(cat) {
  switch (cat) {
    case "user":
      return User;
    case "agent":
      return Bot;
    case "system":
      return Settings;
    case "plan":
      return ListTodo;
    case "solver":
      return Wrench;
    case "aggregate":
      return Puzzle;
    case "pipeline":
      return GitMerge;
    default:
      return Settings;
  }
}
function computeStats(m) {
  const ev = String(m.event || "");
  try {
    let statsList;
    let model;
    let agentName;
    if (ev === "plan.completed" || ev.endsWith("plan.completed")) {
      const c = m.content;
      const md = m.metadata;
      if (Array.isArray(md?.statistics)) statsList = md.statistics;
      else if (Array.isArray(c?.statistics)) statsList = c.statistics;
      if (statsList && statsList.length > 0) {
        const agents = Array.from(new Set(statsList.map((x) => x?.agent).filter(Boolean)));
        agentName = agents.length === 1 ? String(agents[0]) : void 0;
      }
    } else if (ev === "solver.completed" || ev.endsWith("solver.completed")) {
      const c = m.content;
      const res = c?.result;
      const md = m.metadata;
      if (Array.isArray(md?.statistics)) statsList = md.statistics;
      else if (Array.isArray(res?.statistics)) statsList = res.statistics;
      agentName = typeof res?.agent_name === "string" ? res.agent_name : void 0;
      if (typeof res?.model === "string" && res.model) {
        model = res.model;
      }
    } else if (ev === "pipeline.completed" || ev.endsWith("pipeline.completed")) {
      const md = m.metadata;
      if (Array.isArray(md?.statistics)) statsList = md.statistics;
    } else {
      return null;
    }
    if (!statsList || statsList.length === 0) {
      if ((ev === "solver.completed" || ev.endsWith("solver.completed")) && model) {
        return { show: true, model, calls: 0, inputTokens: 0, outputTokens: 0 };
      }
      return null;
    }
    const models = Array.from(
      new Set(
        statsList.map((x) => x?.model || x?.metadata?.model).filter((v) => typeof v === "string" && v)
      )
    );
    if (!model) {
      if (models.length === 1) {
        model = String(models[0]);
      } else if (models.length > 1) {
        model = models.join(", ");
      }
    }
    if (!model && (ev === "plan.completed" || ev.endsWith("plan.completed"))) {
      const md = m.metadata;
      const metrics = md?.metrics;
      const byAgent = metrics?.models?.by_agent;
      const agentMap = agentName && byAgent ? byAgent[agentName] : void 0;
      if (agentMap && typeof agentMap === "object") {
        const keys = Object.keys(agentMap);
        if (keys.length === 1) model = keys[0];
        else if (keys.length > 1) model = keys.join(", ");
      }
    }
    let input = 0;
    let output = 0;
    for (const it of statsList) {
      const i = Number(it?.input_tokens ?? 0);
      const o = Number(it?.output_tokens ?? 0);
      if (Number.isFinite(i)) input += i;
      if (Number.isFinite(o)) output += o;
    }
    return {
      show: true,
      model,
      calls: statsList.length,
      inputTokens: input,
      outputTokens: output
    };
  } catch {
    return null;
  }
}

// src/components/MessageList.tsx
import { jsx as jsx3, jsxs as jsxs2 } from "react/jsx-runtime";
function MessageList({ messages, generating, onConfirm, onDecline }) {
  const ref = useRef2(null);
  useEffect3(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, generating]);
  return /* @__PURE__ */ jsxs2("div", { ref, className: "ma-log", children: [
    messages.map((m, i) => /* @__PURE__ */ jsx3(MessageItem, { m, onConfirm, onDecline }, m.event_id ?? `${i}-${m.timestamp}`)),
    generating && /* @__PURE__ */ jsx3("div", { className: "ma-item ma-system", children: /* @__PURE__ */ jsxs2("div", { className: "ma-msg", children: [
      /* @__PURE__ */ jsx3("div", { className: "ma-muted", children: "[status]" }),
      /* @__PURE__ */ jsxs2("div", { style: { display: "flex", alignItems: "center", gap: 8 }, children: [
        /* @__PURE__ */ jsx3("span", { children: "\u751F\u6210\u4E2D" }),
        /* @__PURE__ */ jsxs2("span", { className: "ma-dots", children: [
          /* @__PURE__ */ jsx3("span", { className: "d1", children: "\xB7" }),
          /* @__PURE__ */ jsx3("span", { className: "d2", children: "\xB7" }),
          /* @__PURE__ */ jsx3("span", { className: "d3", children: "\xB7" })
        ] })
      ] })
    ] }) })
  ] });
}

// src/components/MyAgentConsole.tsx
import { jsx as jsx4 } from "react/jsx-runtime";
function MyAgentConsole({
  className,
  theme = "dark"
}) {
  const { state, sendResponse } = useMyAgent();
  const rootClassName = ["ma-console", `ma-theme-${theme}`, className].filter(Boolean).join(" ");
  return /* @__PURE__ */ jsx4("div", { className: rootClassName, children: /* @__PURE__ */ jsx4(
    MessageList,
    {
      messages: state.messages,
      generating: !!state.generating,
      onConfirm: (msg, payload) => sendResponse(msg.step_id, payload),
      onDecline: (msg, payload) => sendResponse(msg.step_id, payload || { confirmed: false })
    }
  ) });
}
export {
  AgentWSClient,
  MyAgentConsole,
  MyAgentProvider,
  useMyAgent
};
//# sourceMappingURL=index.mjs.map