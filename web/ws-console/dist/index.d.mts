import * as react_jsx_runtime from 'react/jsx-runtime';

interface WebSocketMessage {
    event: string;
    timestamp: string;
    session_id?: string;
    connection_id?: string;
    step_id?: string;
    content?: any;
    show_content?: any;
    metadata?: Record<string, any>;
    seq?: number;
    event_id?: string;
}
type AgentEvent = 'agent.session_created' | 'agent.thinking' | 'agent.tool_call' | 'agent.tool_result' | 'agent.user_confirm' | 'agent.partial_answer' | 'agent.final_answer' | 'agent.llm_message' | 'agent.error' | 'agent.interrupted' | 'plan.start' | 'plan.completed' | 'plan.cancelled' | 'solver.start' | 'solver.completed' | 'solver.cancelled' | 'solver.restarted' | 'aggregate.start' | 'aggregate.completed' | 'pipeline.completed' | 'agent.state_exported' | 'agent.state_restored';
type SystemEvent = 'system.connected' | 'system.heartbeat' | 'system.error' | 'system.notice';
type UserEvent = 'user.create_session' | 'user.message' | 'user.response' | 'user.cancel' | 'user.solve_tasks' | 'user.cancel_task' | 'user.restart_task' | 'user.cancel_plan' | 'user.replan' | 'user.ack' | 'user.request_state' | 'user.reconnect_with_state';
interface ConfirmMessage extends WebSocketMessage {
    event: 'agent.user_confirm';
    step_id: string;
    metadata?: {
        requires_confirmation?: boolean;
        scope?: 'plan' | string;
        plan_summary?: string;
        tasks?: any[];
        [k: string]: any;
    };
}
interface AgentConsoleState {
    connection: 'connected' | 'connecting' | 'disconnected' | 'error';
    messages: WebSocketMessage[];
    currentSessionId?: string;
    pendingConfirm?: ConfirmMessage | null;
    lastEventId?: string | null;
    lastSeq?: number;
    error?: string | null;
    generating?: boolean;
    planRunning?: boolean;
    aggregateRunning?: boolean;
    solverRunning?: number;
    thinking?: boolean;
}
interface MyAgentProviderProps {
    wsUrl: string;
    token?: string;
    autoReconnect?: boolean;
    showSystemLogs?: boolean;
    onEvent?: (m: WebSocketMessage) => void;
    children?: any;
}

type Listener = (m: WebSocketMessage) => void;
interface AgentWSClientOptions {
    url: string;
    token?: string;
    autoReconnect?: boolean;
    ackIntervalMs?: number;
    onOpen?: () => void;
    onClose?: (ev?: any) => void;
    onError?: (err: any) => void;
}
declare class AgentWSClient {
    private ws;
    private opts;
    private listeners;
    private reconnectTimer;
    private lastEventId;
    private lastSeq;
    private ackTimer;
    private connected;
    constructor(opts: AgentWSClientOptions);
    isOpen(): boolean;
    getLastEvent(): {
        lastEventId: string | null;
        lastSeq: number;
    };
    onMessage(fn: Listener): () => void;
    connect(): void;
    disconnect(): void;
    private scheduleReconnect;
    private startAckLoop;
    private stopAckLoop;
    private buildUrlWithToken;
    send(payload: any): void;
}

interface Ctx {
    state: AgentConsoleState;
    client: AgentWSClient | null;
    createSession: (content?: any) => void;
    sendUserMessage: (content: any) => void;
    sendResponse: (stepId: string, content: any) => void;
    cancel: () => void;
    solveTasks: (tasks: any[], extras?: {
        question?: string;
        plan_summary?: string;
    }) => void;
    cancelTask: (taskId: string | number) => void;
    restartTask: (taskId: string | number) => void;
    cancelPlan: () => void;
    replan: (question?: string) => void;
    requestState: () => void;
    reconnectWithState: (signedState: any, last?: {
        last_event_id?: string;
        last_seq?: number;
    }) => void;
}
declare function MyAgentProvider(props: MyAgentProviderProps): react_jsx_runtime.JSX.Element;
declare function useMyAgent(): Ctx;

declare function MyAgentConsole({ className }: {
    className?: string;
}): react_jsx_runtime.JSX.Element;

export { type AgentConsoleState, type AgentEvent, AgentWSClient, type ConfirmMessage, MyAgentConsole, MyAgentProvider, type SystemEvent, type UserEvent, type WebSocketMessage, useMyAgent };
