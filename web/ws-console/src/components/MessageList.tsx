import React, { useEffect, useRef } from 'react';
import type { WebSocketMessage, ConfirmMessage } from '../types';
import { MessageItem } from './MessageItem';

export function MessageList({ messages, generating, onConfirm, onDecline }: { messages: WebSocketMessage[]; generating?: boolean; onConfirm?: (msg: ConfirmMessage, payload: { confirmed: boolean; tasks?: any[] }) => void; onDecline?: (msg: ConfirmMessage, payload?: { confirmed: boolean }) => void }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, generating]);
  return (
    <div ref={ref} className="ma-log">
      {messages.map((m, i) => (
        <MessageItem key={m.event_id ?? `${i}-${m.timestamp}`} m={m} onConfirm={onConfirm} onDecline={onDecline} />
      ))}
      {generating && (
        <div className="ma-item ma-system">
          <div className="ma-msg">
            <div className="ma-muted">[status]</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>生成中</span>
              <span className="ma-dots"><span className="d1">·</span><span className="d2">·</span><span className="d3">·</span></span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
