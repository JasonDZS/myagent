import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';

export function UserInput({ onSend, disabled, generating, onCancel }: { onSend: (text: string) => void; disabled?: boolean; generating?: boolean; onCancel?: () => void }) {
  const [text, setText] = useState('');
  const send = () => {
    const v = text.trim();
    if (!v) return;
    onSend(v);
    setText('');
  };
  return (
    <div className="ma-input">
      <input
        className="ma-text"
        placeholder="输入你的消息..."
        value={text}
        disabled={disabled || generating}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (!generating && e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
          }
        }}
      />
      {generating ? (
        <button className="ma-btn ma-send" onClick={onCancel}>
          <Loader2 size={16} className="ma-spin" />
          <span style={{ marginLeft: 6 }}>打断</span>
        </button>
      ) : (
        <button className="ma-btn ma-send" disabled={disabled} onClick={send}>
          发送
        </button>
      )}
    </div>
  );
}
