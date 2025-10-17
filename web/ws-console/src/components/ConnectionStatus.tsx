import React from 'react';

export function ConnectionStatus({ status }: { status: 'connected' | 'connecting' | 'disconnected' | 'error' }) {
  return (
    <div className="ma-status" title={`Connection: ${status}`}>
      <span className={`ma-dot ${status}`} />
      <span>{status}</span>
    </div>
  );
}

