import React from 'react';
import { useMyAgent } from '../provider';
import { MessageList } from './MessageList';

export function MyAgentConsole({
  className,
  theme = 'dark',
}: {
  className?: string;
  theme?: 'dark' | 'light';
}) {
  const { state, sendResponse } = useMyAgent();
  const rootClassName = ['ma-console', `ma-theme-${theme}`, className].filter(Boolean).join(' ');

  return (
    <div className={rootClassName}>
      <MessageList
        messages={state.messages}
        generating={!!state.generating}
        onConfirm={(msg, payload) => sendResponse(msg.step_id, payload)}
        onDecline={(msg, payload) => sendResponse(msg.step_id, payload || { confirmed: false })}
      />
    </div>
  );
}
