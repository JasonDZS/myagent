/**
 * MyAgent WebSocket Event Types - TypeScript Definitions
 *
 * Auto-generated type definitions for all event types.
 * Use these for frontend type checking and IDE autocompletion.
 */

// ============================================================================
// Base Protocol
// ============================================================================

export interface EventProtocol {
  session_id?: string;
  connection_id?: string;
  step_id?: string;
  event: string;
  timestamp: string;
  content?: string | Record<string, any> | null;
  metadata?: Record<string, any>;
}

// ============================================================================
// User Events (Client → Server)
// ============================================================================

export interface UserCreateSession extends EventProtocol {
  event: "user.create_session";
  content?: {
    project_name?: string;
    session_name?: string;
    config?: Record<string, any>;
  };
  metadata?: {
    client_version?: string;
    client_id?: string;
  };
}

export interface UserMessage extends EventProtocol {
  session_id: string;
  event: "user.message";
  content: string;
  metadata?: {
    message_type?: "query" | "instruction" | "feedback";
    priority?: "low" | "normal" | "high";
    source?: string;
  };
}

export interface UserResponse extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "user.response";
  content: {
    approved: boolean;
    feedback?: string;
    data?: Record<string, any>;
  };
  metadata?: {
    response_time_ms?: number;
    user_action?: "approve" | "reject" | "modify";
  };
}

export interface UserAck extends EventProtocol {
  session_id: string;
  event: "user.ack";
  content?: {
    last_seq: number;
  };
  metadata?: {
    received_count?: number;
    buffer_size?: number;
  };
}

export interface UserCancel extends EventProtocol {
  session_id: string;
  event: "user.cancel";
  content?: {
    reason?: string;
  };
}

export interface UserReconnect extends EventProtocol {
  event: "user.reconnect";
  content: {
    session_id: string;
    last_seq?: number;
  };
}

export interface UserReconnectWithState extends EventProtocol {
  event: "user.reconnect_with_state";
  content: {
    signed_state: string;
    last_seq: number;
    last_event_id?: string;
  };
  metadata?: {
    offline_duration_ms: number;
    state_version: string;
  };
}

export interface UserRequestState extends EventProtocol {
  session_id: string;
  event: "user.request_state";
  metadata?: {
    include_history?: boolean;
    compression?: "gzip" | "none";
  };
}

export type UserEvent =
  | UserCreateSession
  | UserMessage
  | UserResponse
  | UserAck
  | UserCancel
  | UserReconnect
  | UserReconnectWithState
  | UserRequestState;

// ============================================================================
// Plan Events (Server → Client)
// ============================================================================

export interface PlanStart extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "plan.start";
  content: {
    question: string;
    context?: string;
  };
  metadata: {
    plan_id: string;
    timeout_seconds: number;
    model: string;
  };
}

export interface PlanCompleted extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "plan.completed";
  content: {
    tasks: Array<{
      id: string;
      title: string;
      description: string;
      estimated_duration_sec?: number;
    }>;
  };
  metadata: {
    task_count: number;
    plan_summary: string;
    total_estimated_tokens: number;
    llm_calls: number;
    planning_time_ms: number;
  };
}

export interface PlanStepCompleted extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "plan.step_completed";
  content: {
    step_name: string;
    step_result: any;
  };
  metadata: {
    step_index: number;
    step_duration_ms: number;
    tokens_used: number;
  };
}

export interface PlanValidationError extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "plan.validation_error";
  content: {
    error_message: string;
    field?: string;
    constraint?: string;
  };
  metadata: {
    error_code: string;
    validation_errors: Array<string>;
  };
}

export interface PlanCancelled extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "plan.cancelled";
  content?: string;
  metadata: {
    reason: "user_request" | "timeout" | "error" | "resource_limit";
    partial_plan?: Array<{
      id: string;
      title: string;
      description: string;
    }>;
    cancellation_time_ms: number;
  };
}

export interface PlanCoercionError extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "plan.coercion_error";
  content?: string;
  metadata: {
    error_code: string;
    raw_output?: string;
    error_type: string;
    recovery_action: "retry" | "manual_input" | "fallback" | "abort";
    attempt?: number;
    max_attempts?: number;
  };
}

export type PlanEvent =
  | PlanStart
  | PlanCompleted
  | PlanStepCompleted
  | PlanValidationError
  | PlanCancelled
  | PlanCoercionError;

// ============================================================================
// Solver Events (Server → Client)
// ============================================================================

export interface SolverStart extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "solver.start";
  metadata: {
    task_count: number;
    total_tasks: number;
    estimated_duration_sec: number;
  };
}

export interface SolverProgress extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "solver.progress";
  content?: {
    current_task: string;
    status: string;
  };
  metadata: {
    progress_percent: number;
    current_step: number;
    completed_steps: number;
    total_steps: number;
    elapsed_time_ms: number;
    estimated_remaining_ms?: number;
  };
}

export interface SolverCompleted extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "solver.completed";
  content: {
    task_results: Array<{
      task_id: string;
      result: any;
      status: "success" | "failed" | "partial";
    }>;
  };
  metadata: {
    total_tasks: number;
    successful_tasks: number;
    failed_tasks: number;
    total_execution_time_ms: number;
    total_tokens_used: number;
  };
}

export interface SolverStepFailed extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "solver.step_failed";
  content: {
    error_message: string;
    step_name: string;
  };
  metadata: {
    step_index: number;
    error_code: string;
    error_type: string;
    recovery_possible: boolean;
  };
}

export interface SolverRetry extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "solver.retry";
  content?: {
    step_name: string;
  };
  metadata: {
    attempt: number;
    max_attempts: number;
    backoff_ms: number;
  };
}

export interface SolverCancelled extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "solver.cancelled";
  content?: string;
  metadata: {
    task_id: string;
    reason: "user_request" | "dependency_failed" | "timeout" | "resource_limit";
    execution_time_ms: number;
    partial_result?: Record<string, any>;
  };
}

export interface SolverRestarted extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "solver.restarted";
  content?: string;
  metadata: {
    task_id: string;
    previous_error?: string;
    attempt: number;
    max_attempts: number;
    reason: "retry_after_error" | "user_request" | "escalation";
    backoff_ms: number;
  };
}

export type SolverEvent =
  | SolverStart
  | SolverProgress
  | SolverCompleted
  | SolverStepFailed
  | SolverRetry
  | SolverCancelled
  | SolverRestarted;

// ============================================================================
// Agent Events (Server → Client)
// ============================================================================

export interface AgentThinking extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "agent.thinking";
  content: string;
  metadata: {
    model: string;
    max_tokens: number;
    temperature: number;
    thinking_type: "analysis" | "planning" | "reasoning";
  };
}

export interface AgentToolCall extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "agent.tool_call";
  content: {
    tool_name: string;
    tool_description: string;
    arguments: Record<string, any>;
  };
  metadata: {
    call_id: string;
    tool_type: string;
    estimated_duration_ms?: number;
  };
}

export interface AgentToolResult extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "agent.tool_result";
  content: {
    result: any;
    status: "success" | "failed";
  };
  metadata: {
    call_id: string;
    execution_time_ms: number;
    tokens_used?: number;
  };
}

export interface AgentPartialAnswer extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "agent.partial_answer";
  content: string;
  metadata: {
    chunk_index: number;
    completion_percent?: number;
  };
}

export interface AgentFinalAnswer extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "agent.final_answer";
  content: {
    answer: string;
    answer_type: "text" | "json" | "code" | "structured";
  };
  metadata: {
    generation_time_ms: number;
    total_tokens_used: number;
    model: string;
  };
}

export interface AgentUserConfirm extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "agent.user_confirm";
  content: {
    message: string;
    confirmation_type: "approve" | "select" | "input";
    options?: Array<{
      id: string;
      label: string;
      description?: string;
    }>;
  };
  metadata: {
    timeout_seconds?: number;
    critical: boolean;
  };
}

export interface AgentSessionCreated extends EventProtocol {
  session_id: string;
  event: "agent.session_created";
  content: string;
  metadata: {
    agent_name: string;
    agent_type: string;
  };
}

export interface AgentSessionEnd extends EventProtocol {
  session_id: string;
  event: "agent.session_end";
  content: string;
  metadata: {
    reason: string;
    total_duration_ms: number;
  };
}

export interface AgentLLMMessage extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "agent.llm_message";
  content: string;
  metadata: {
    model: string;
    message_id?: string;
    role?: "user" | "assistant" | "system";
    index?: number;
    tokens?: number;
  };
}

export interface AgentStateExported extends EventProtocol {
  session_id: string;
  event: "agent.state_exported";
  content?: {
    exported_state: Record<string, any>;
  };
  metadata: {
    exported_at: string;
    valid_until: string;
    state_size_bytes?: number;
    checksum?: string;
  };
}

export interface AgentStateRestored extends EventProtocol {
  session_id: string;
  event: "agent.state_restored";
  content?: string;
  metadata: {
    restored_at: string;
    restoration_time_ms: number;
    previous_stage: string;
    recovered_tasks?: number;
    state_integrity: "verified" | "partial" | "failed";
  };
}

export type AgentEvent =
  | AgentThinking
  | AgentToolCall
  | AgentToolResult
  | AgentPartialAnswer
  | AgentFinalAnswer
  | AgentUserConfirm
  | AgentSessionCreated
  | AgentSessionEnd
  | AgentLLMMessage
  | AgentStateExported
  | AgentStateRestored;

// ============================================================================
// System Events (Bidirectional)
// ============================================================================

export interface SystemConnected extends EventProtocol {
  connection_id: string;
  event: "system.connected";
  content: {
    server_version: string;
    server_time: string;
  };
  metadata: {
    server_uptime_seconds: number;
    active_sessions: number;
  };
}

export interface SystemHeartbeat extends EventProtocol {
  event: "system.heartbeat";
  content?: {
    server_time: string;
  };
  metadata: {
    seq: number;
    server_uptime_seconds: number;
  };
}

export interface SystemNotice extends EventProtocol {
  event: "system.notice";
  content: {
    message: string;
    event_list?: Array<Record<string, any>>;
  };
  metadata: {
    type: "info" | "warning" | "maintenance";
    severity: "low" | "medium" | "high";
  };
}

export interface SystemError extends EventProtocol {
  event: "system.error";
  content: string;
  metadata: {
    error_code: string;
    severity: "info" | "warning" | "error";
  };
}

export type SystemEvent =
  | SystemConnected
  | SystemHeartbeat
  | SystemNotice
  | SystemError;

// ============================================================================
// Error Events (Server → Client)
// ============================================================================

export interface ErrorValidation extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "error.validation";
  content: string;
  metadata: {
    error_code: "ERR_VALIDATION_400";
    field?: string;
    constraint?: string;
    recoverable: boolean;
  };
}

export interface ErrorTimeout extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "error.timeout";
  content: string;
  metadata: {
    error_code: "ERR_TIMEOUT_500";
    timeout_seconds: number;
    elapsed_seconds: number;
    stage: string;
    attempt: number;
    max_attempts: number;
    retry_after_ms: number;
    recovery_strategy: string;
  };
}

export interface ErrorExecution extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "error.execution";
  content: string;
  metadata: {
    error_code: "ERR_EXECUTION_600";
    error_type: string;
    context: Record<string, any>;
    recoverable: boolean;
  };
}

export interface ErrorRetry extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "error.retry";
  content?: string;
  metadata: {
    attempt: number;
    max_attempts: number;
    delay_ms: number;
    error: string;
  };
}

export interface ErrorRecoveryStarted extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "error.recovery_started";
  content: string;
  metadata: {
    recovery_action: string;
    estimated_duration_ms?: number;
  };
}

export interface ErrorRecoverySuccess extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "error.recovery_success";
  content?: string;
  metadata: {
    recovery_time_ms: number;
    attempts: number;
  };
}

export interface ErrorRecoveryFailed extends EventProtocol {
  session_id: string;
  step_id: string;
  event: "error.recovery_failed";
  content: string;
  metadata: {
    error_code: string;
    attempts: number;
    original_error: string;
    recovery_error: string;
  };
}

export type ErrorEvent =
  | ErrorValidation
  | ErrorTimeout
  | ErrorExecution
  | ErrorRetry
  | ErrorRecoveryStarted
  | ErrorRecoverySuccess
  | ErrorRecoveryFailed;

// ============================================================================
// Union Type - All Events
// ============================================================================

export type AnyEvent =
  | UserEvent
  | PlanEvent
  | SolverEvent
  | AgentEvent
  | SystemEvent
  | ErrorEvent;

// ============================================================================
// Event Handlers
// ============================================================================

export type EventHandler<T extends EventProtocol = AnyEvent> = (event: T) => Promise<void> | void;

export type EventHandlers = Partial<Record<AnyEvent["event"], EventHandler>>;

// ============================================================================
// Type Guards
// ============================================================================

export function isUserEvent(event: EventProtocol): event is UserEvent {
  return event.event.startsWith("user.");
}

export function isPlanEvent(event: EventProtocol): event is PlanEvent {
  return event.event.startsWith("plan.");
}

export function isSolverEvent(event: EventProtocol): event is SolverEvent {
  return event.event.startsWith("solver.");
}

export function isAgentEvent(event: EventProtocol): event is AgentEvent {
  return event.event.startsWith("agent.");
}

export function isSystemEvent(event: EventProtocol): event is SystemEvent {
  return event.event.startsWith("system.");
}

export function isErrorEvent(event: EventProtocol): event is ErrorEvent {
  return event.event.startsWith("error.");
}

// ============================================================================
// Event Constants
// ============================================================================

export const USER_EVENTS = {
  CREATE_SESSION: "user.create_session" as const,
  MESSAGE: "user.message" as const,
  RESPONSE: "user.response" as const,
  ACK: "user.ack" as const,
  CANCEL: "user.cancel" as const,
  RECONNECT: "user.reconnect" as const,
  RECONNECT_WITH_STATE: "user.reconnect_with_state" as const,
  REQUEST_STATE: "user.request_state" as const,
};

export const PLAN_EVENTS = {
  START: "plan.start" as const,
  COMPLETED: "plan.completed" as const,
  STEP_COMPLETED: "plan.step_completed" as const,
  VALIDATION_ERROR: "plan.validation_error" as const,
  CANCELLED: "plan.cancelled" as const,
  COERCION_ERROR: "plan.coercion_error" as const,
};

export const SOLVER_EVENTS = {
  START: "solver.start" as const,
  PROGRESS: "solver.progress" as const,
  COMPLETED: "solver.completed" as const,
  STEP_FAILED: "solver.step_failed" as const,
  RETRY: "solver.retry" as const,
  CANCELLED: "solver.cancelled" as const,
  RESTARTED: "solver.restarted" as const,
};

export const AGENT_EVENTS = {
  THINKING: "agent.thinking" as const,
  TOOL_CALL: "agent.tool_call" as const,
  TOOL_RESULT: "agent.tool_result" as const,
  PARTIAL_ANSWER: "agent.partial_answer" as const,
  FINAL_ANSWER: "agent.final_answer" as const,
  USER_CONFIRM: "agent.user_confirm" as const,
  SESSION_CREATED: "agent.session_created" as const,
  SESSION_END: "agent.session_end" as const,
  LLM_MESSAGE: "agent.llm_message" as const,
  STATE_EXPORTED: "agent.state_exported" as const,
  STATE_RESTORED: "agent.state_restored" as const,
};

export const SYSTEM_EVENTS = {
  CONNECTED: "system.connected" as const,
  NOTICE: "system.notice" as const,
  HEARTBEAT: "system.heartbeat" as const,
  ERROR: "system.error" as const,
};

export const ERROR_EVENTS = {
  VALIDATION: "error.validation" as const,
  TIMEOUT: "error.timeout" as const,
  EXECUTION: "error.execution" as const,
  RETRY: "error.retry" as const,
  RECOVERY_STARTED: "error.recovery_started" as const,
  RECOVERY_SUCCESS: "error.recovery_success" as const,
  RECOVERY_FAILED: "error.recovery_failed" as const,
};
