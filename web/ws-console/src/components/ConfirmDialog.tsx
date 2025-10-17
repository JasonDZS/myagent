import React, { useMemo, useState } from 'react';
import type { ConfirmMessage } from '../types';

export function ConfirmDialog({ confirm, onConfirm, onDecline }: { confirm: ConfirmMessage; onConfirm: (payload: { confirmed: boolean; tasks?: any[] }) => void; onDecline: (payload?: { confirmed: boolean }) => void }) {
  const tasks = useMemo<any[] | null>(() => {
    const t = confirm?.metadata?.tasks;
    return Array.isArray(t) ? t : null;
  }, [confirm]);
  const [json, setJson] = useState(() => (tasks ? JSON.stringify(tasks, null, 2) : ''));
  const [err, setErr] = useState<string | null>(null);
  const hasEditable = Boolean(tasks);
  const scope = (confirm?.metadata?.scope as string) || 'plan';
  const title = scope === 'plan' ? '确认规划任务' : '确认操作';

  const handleConfirm = () => {
    if (hasEditable) {
      try {
        const parsed = JSON.parse(json || '[]');
        if (!Array.isArray(parsed)) throw new Error('JSON 必须为数组');
        onConfirm({ confirmed: true, tasks: parsed });
      } catch (e: any) {
        setErr(String(e?.message || e));
        return;
      }
    } else {
      onConfirm({ confirmed: true });
    }
  };

  return (
    <div className="ma-confirm">
      <div className="ma-dialog">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <span className="ma-muted">step: {confirm.step_id}</span>
        </div>
        {confirm.metadata?.plan_summary && <div className="ma-muted">{confirm.metadata.plan_summary}</div>}
        {hasEditable ? (
          <>
            <div className="ma-muted">可以编辑下方 JSON 以修改任务：</div>
            <textarea className="ma-json" value={json} onChange={(e) => setJson(e.target.value)} />
            {err && <div style={{ color: '#ef4444' }}>{err}</div>}
          </>
        ) : (
          <div className="ma-muted">是否继续执行？</div>
        )}
        <div className="ma-row">
          <button className="ma-btn" onClick={() => onDecline({ confirmed: false })}>取消</button>
          <button className="ma-btn" onClick={handleConfirm}>确认</button>
        </div>
      </div>
    </div>
  );
}

