export interface WebSocketMessage {
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

export type AgentEvent =
  | 'agent.session_created'
  | 'agent.thinking'
  | 'agent.tool_call'
  | 'agent.tool_result'
  | 'agent.user_confirm'
  | 'agent.partial_answer'
  | 'agent.final_answer'
  | 'agent.llm_message'
  | 'agent.error'
  | 'agent.interrupted'
  | 'plan.start'
  | 'plan.completed'
  | 'plan.cancelled'
  | 'solver.start'
  | 'solver.completed'
  | 'solver.cancelled'
  | 'solver.restarted'
  | 'aggregate.start'
  | 'aggregate.completed'
  | 'pipeline.completed'
  | 'agent.state_exported'
  | 'agent.state_restored';

export type SystemEvent = 'system.connected' | 'system.heartbeat' | 'system.error' | 'system.notice';

export type UserEvent =
  | 'user.create_session'
  | 'user.message'
  | 'user.response'
  | 'user.cancel'
  | 'user.solve_tasks'
  | 'user.cancel_task'
  | 'user.restart_task'
  | 'user.cancel_plan'
  | 'user.replan'
  | 'user.ack'
  | 'user.request_state'
  | 'user.reconnect_with_state';

export interface ConfirmMessage extends WebSocketMessage {
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

export interface AgentConsoleState {
  connection: 'connected' | 'connecting' | 'disconnected' | 'error';
  messages: WebSocketMessage[];
  currentSessionId?: string;
  pendingConfirm?: ConfirmMessage | null;
  lastEventId?: string | null;
  lastSeq?: number;
  error?: string | null;
  // runtime tracking
  generating?: boolean;
  planRunning?: boolean;
  aggregateRunning?: boolean;
  solverRunning?: number;
  thinking?: boolean;
}

export interface MyAgentProviderProps {
  wsUrl: string;
  token?: string;
  autoReconnect?: boolean;
  showSystemLogs?: boolean;
  onEvent?: (m: WebSocketMessage) => void;
  children?: any;
}

export interface SendOptions {
  step_id?: string;
}
