export type {
  WebSocketMessage,
  AgentEvent,
  SystemEvent,
  UserEvent,
  ConfirmMessage,
  AgentConsoleState,
} from './types';

export { MyAgentProvider, useMyAgent } from './provider';
export { MyAgentConsole } from './components/MyAgentConsole';

// Optional: standalone client for non-React usage
export { AgentWSClient } from './ws-client';

// Styles (consumers can import as needed)
// import './styles.css'

