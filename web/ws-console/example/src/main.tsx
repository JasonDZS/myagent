import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import '@myagent/ws-console/styles.css';
import { MyAgentProvider } from '@myagent/ws-console';
import { MyAgentConsole } from '@myagent/ws-console';

const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8080';

function SplitView({ children }: { children: [React.ReactNode, React.ReactNode] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [leftWidth, setLeftWidth] = useState<number>(() => Math.max(200, Math.floor(window.innerWidth * 0.4)));
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const minLeft = 100; // min width px
      const maxLeft = rect.width - 250; // keep right usable
      const next = Math.min(maxLeft, Math.max(minLeft, e.clientX - rect.left));
      setLeftWidth(next);
      e.preventDefault();
    };
    const onUp = () => setDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dragging]);

  return (
    <div ref={containerRef} style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: '#0b0d12' }}>
      <div style={{ width: leftWidth, borderRight: '1px solid #1f2633', background: '#0b0d12' }} />
      <div
        role="separator"
        onMouseDown={() => setDragging(true)}
        style={{ width: 6, cursor: 'col-resize', background: dragging ? '#334155' : '#1f2633' }}
        title="拖拽调整左右布局"
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        {children[1]}
      </div>
    </div>
  );
}

function App() {
  return (
    <MyAgentProvider wsUrl={WS_URL} autoReconnect>
      <SplitView>
        {[
          <div key="left" />, // 空白左栏
          <div key="right" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <MyAgentConsole />
          </div>,
        ] as any}
      </SplitView>
    </MyAgentProvider>
  );
}

createRoot(document.getElementById('root')!).render(<App />);

