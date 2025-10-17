import React from 'react';
import { useMyAgent } from '../provider';
import { MessageList } from './MessageList';
import { UserInput } from './UserInput';
import { ConnectionStatus } from './ConnectionStatus';

export function MyAgentConsole({
  className,
  theme = 'dark',
}: {
  className?: string;
  theme?: 'dark' | 'light';
}) {
  const { state, createSession, sendUserMessage, sendResponse, requestState, reconnectWithState, cancel, selectSession } = useMyAgent();

  const onMountCreate = React.useRef(false);
  React.useEffect(() => {
    if (state.connection === 'connected' && !state.currentSessionId && !onMountCreate.current) {
      onMountCreate.current = true;
      createSession();
    }
  }, [state.connection, state.currentSessionId, createSession]);

  const rootClassName = ['ma-console', `ma-theme-${theme}`, className].filter(Boolean).join(' ');
  const sessionOptions = state.availableSessions ?? [];
  const fallbackSessionId = sessionOptions.length > 0 ? sessionOptions[0]?.sessionId ?? '' : '';
  const activeSessionId = state.viewSessionId ?? state.currentSessionId ?? fallbackSessionId;
  const canSelect = sessionOptions.length > 0;
  const viewingActiveSession = !state.viewSessionId || state.viewSessionId === state.currentSessionId;
  const inputDisabled = !state.currentSessionId || state.connection !== 'connected' || !viewingActiveSession;
  const listGenerating = viewingActiveSession ? !!state.generating : false;

  return (
    <div className={rootClassName}>
      <div className="ma-header">
        <div className="ma-header-main">
          <ConnectionStatus status={state.connection} />
          <div className="ma-session-switcher">
            <label className="ma-session-label" htmlFor="ma-session-select">会话</label>
            <select
              id="ma-session-select"
              className="ma-select"
              value={canSelect ? activeSessionId : ''}
              onChange={(ev) => selectSession(ev.target.value)}
              disabled={!canSelect}
            >
              {!canSelect && <option value="">暂无会话</option>}
              {canSelect && sessionOptions.map((session) => {
                const label = session.sessionId.length > 12
                  ? `${session.sessionId.slice(0, 6)}…${session.sessionId.slice(-4)}`
                  : session.sessionId;
                return (
                  <option key={session.sessionId} value={session.sessionId} title={session.sessionId}>
                    {label}
                  </option>
                );
              })}
            </select>
          </div>
        </div>
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
      {!viewingActiveSession && (
        <div className="ma-banner">
          <span className="ma-muted">正在查看历史会话，无法发送新消息</span>
        </div>
      )}
      <MessageList
        messages={state.messages}
        generating={listGenerating}
        onConfirm={(msg, payload) => sendResponse(msg.step_id, payload)}
        onDecline={(msg, payload) => sendResponse(msg.step_id, payload || { confirmed: false })}
      />
      <UserInput
        onSend={sendUserMessage}
        disabled={inputDisabled}
        generating={!!state.generating}
        onCancel={() => cancel()}
      />
    </div>
  );
}
