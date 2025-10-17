import React from 'react';
import { useMyAgent } from '../provider';
import { MessageList } from './MessageList';
import { UserInput } from './UserInput';
import { ConnectionStatus } from './ConnectionStatus';

export function MyAgentConsole({ className }: { className?: string }) {
  const { state, createSession, sendUserMessage, sendResponse, requestState, reconnectWithState, cancel } = useMyAgent();

  const onMountCreate = React.useRef(false);
  React.useEffect(() => {
    if (state.connection === 'connected' && !state.currentSessionId && !onMountCreate.current) {
      onMountCreate.current = true;
      createSession();
    }
  }, [state.connection, state.currentSessionId, createSession]);

  return (
    <div className={`ma-console ${className ?? ''}`.trim()}>
      <div className="ma-header">
        <ConnectionStatus status={state.connection} />
        <div className="ma-actions">
          <button className="ma-btn" onClick={() => createSession()}>新建会话</button>
          <button className="ma-btn" onClick={() => requestState()}>导出状态</button>
          <button
            className="ma-btn"
            onClick={() => {
              try {
                const raw = typeof localStorage !== 'undefined' ? localStorage.getItem('ma_state_latest') : null;
                if (!raw) return;
                const signed = JSON.parse(raw);
                const last: any = state.lastEventId ? { last_event_id: state.lastEventId } : { last_seq: state.lastSeq };
                reconnectWithState(signed, last);
              } catch {}
            }}
          >
            恢复状态
          </button>
        </div>
      </div>
      <MessageList
        messages={state.messages}
        generating={state.generating}
        onConfirm={(msg, payload) => sendResponse(msg.step_id, payload)}
        onDecline={(msg, payload) => sendResponse(msg.step_id, payload || { confirmed: false })}
      />
      <UserInput
        onSend={sendUserMessage}
        disabled={!state.currentSessionId || state.connection !== 'connected'}
        generating={!!state.generating}
        onCancel={() => cancel()}
      />
    </div>
  );
}
