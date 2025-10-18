import React, { useEffect, useMemo, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import { User, Bot, Settings, ListTodo, Wrench, Puzzle, GitMerge, Cpu, Hash, LogIn, LogOut } from 'lucide-react';
import type { WebSocketMessage, ConfirmMessage } from '../types';

function stringifyContent(content: any): string {
  if (content == null) return '';
  if (typeof content === 'string') return content;
  try {
    return JSON.stringify(content, null, 2);
  } catch {
    return String(content);
  }
}

function friendlyFromClientFallback(m: WebSocketMessage): string | undefined {
  const ev = String(m.event || '');
  const c: any = (m as any).content;
  const md: any = (m as any).metadata || {};
  try {
    if (ev === 'system.connected') return '已连接到服务器';
    if (ev === 'system.error') return typeof c === 'string' ? `系统错误：${c}` : '系统错误';
    if (ev === 'agent.session_created') return '会话创建成功';
    if (ev === 'agent.thinking') return '正在思考…';
    if (ev === 'agent.partial_answer') return typeof c === 'string' ? c : '生成中…';
    if (ev === 'agent.final_answer') return typeof c === 'string' ? c : '已生成答案';
    if (ev === 'agent.user_confirm') {
      const scope = md?.scope || 'plan';
      const tasks = Array.isArray(md?.tasks) ? md.tasks : undefined;
      const count = tasks ? tasks.length : undefined;
      const sum = typeof md?.plan_summary === 'string' ? md.plan_summary : undefined;
      return scope === 'plan'
        ? `请确认规划${count != null ? `（${count} 个任务）` : ''}${sum ? `：${sum}` : ''}`
        : '请确认操作';
    }
    if (ev === 'plan.start') return typeof c?.question === 'string' ? `开始规划：${c.question}` : '开始规划';
    if (ev === 'plan.completed') {
      const tasks = Array.isArray(c?.tasks) ? c.tasks : undefined;
      const count = tasks ? tasks.length : undefined;
      const sum = typeof c?.plan_summary === 'string' ? c.plan_summary : undefined;
      return `规划完成${count != null ? `（${count} 个任务）` : ''}${sum ? `：${sum}` : ''}`;
    }
    if (ev === 'solver.start') {
      const task = c?.task;
      const title = typeof task?.title === 'string' ? task.title : (typeof task?.name === 'string' ? task.name : undefined);
      return title ? `开始求解：${title}` : '开始求解';
    }
    if (ev === 'solver.completed') {
      const task = c?.task;
      const title = typeof task?.title === 'string' ? task.title : (typeof task?.name === 'string' ? task.name : undefined);
      return title ? `求解完成：${title}` : '求解完成';
    }
    if (ev === 'aggregate.start') return '开始聚合';
    if (ev === 'aggregate.completed') return '聚合完成';
    if (ev === 'pipeline.completed') return '流水线完成';
  } catch {}
  return undefined;
}

export function MessageItem({ m, onConfirm, onDecline }: { m: WebSocketMessage; onConfirm?: (msg: ConfirmMessage, payload: { confirmed: boolean; tasks?: any[] }) => void; onDecline?: (msg: ConfirmMessage, payload?: { confirmed: boolean }) => void }) {
  const event = String(m.event || '');
  let role: 'agent' | 'user' | 'system' = 'system';
  if (event.startsWith('agent.') || event.startsWith('plan.') || event.startsWith('solver.') || event.startsWith('aggregate.') || event === 'pipeline.completed') role = 'agent';
  if (event.startsWith('user.')) role = 'user';
  const cls = `ma-item ma-${role}`;
  const label = event.replace(/^.*\./, '');
  const preferred = typeof (m as any).show_content === 'string' ? (m as any).show_content : friendlyFromClientFallback(m);
  const body = stringifyContent(preferred ?? m.content);
  const ts = m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : '';
  const stats = useMemo(() => computeStats(m), [m]);
  // Determine confirm early to set default collapsed state
  const isConfirm = event === 'agent.user_confirm';
  const [collapsed, setCollapsed] = useState<boolean>(() => !isConfirm);
  const category = getCategory(event);
  const Icon = getIcon(category);

  const preview = useMemo(() => {
    const s = body.replace(/\s+/g, ' ').trim();
    return s.length > 140 ? s.slice(0, 140) + '…' : s;
  }, [body]);

  // Inline confirmation UI inside the message list
  const confirm = (isConfirm ? (m as ConfirmMessage) : undefined) as ConfirmMessage | undefined;
  const tasks = useMemo<any[] | null>(() => {
    const t = confirm?.metadata?.tasks;
    return Array.isArray(t) ? t : null;
  }, [confirm]);
  const [json, setJson] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [selection, setSelection] = useState<null | 'confirmed' | 'declined'>(null);
  type EditMode = 'form' | 'json';
  const [editMode, setEditMode] = useState<EditMode>('form');
  const [formTasks, setFormTasks] = useState<any[]>([]);
  useEffect(() => {
    if (isConfirm) {
      setJson(tasks ? JSON.stringify(tasks, null, 2) : '');
      setErr(null);
      setSent(false);
      setSelection(null);
      setCollapsed(false); // default expand confirm messages
      setEditMode('form');
      try {
        setFormTasks(Array.isArray(tasks) ? tasks.map((t) => (t && typeof t === 'object' ? { ...t } : t)) : []);
      } catch {
        setFormTasks([]);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConfirm, confirm?.step_id]);
  const scope = (confirm?.metadata?.scope as string) || 'plan';
  const title = scope === 'plan' ? '确认规划任务' : '确认操作';
  const planSummary = confirm?.metadata?.plan_summary as string | undefined;
  const hasEditable = Boolean(tasks);

  if (isConfirm) {
    const handleConfirm = () => {
      if (sent) return;
      if (hasEditable) {
        try {
          let finalTasks: any[] = [];
          if (editMode === 'json') {
            const parsed = JSON.parse(json || '[]');
            if (!Array.isArray(parsed)) throw new Error('JSON 必须为数组');
            finalTasks = parsed;
          } else {
            finalTasks = Array.isArray(formTasks) ? formTasks : [];
          }
          onConfirm?.(confirm!, { confirmed: true, tasks: finalTasks });
          setSelection('confirmed');
          setSent(true);
          setCollapsed(true);
        } catch (e: any) {
          setErr(String(e?.message || e));
          return;
        }
      } else {
        onConfirm?.(confirm!, { confirmed: true });
        setSelection('confirmed');
        setSent(true);
        setCollapsed(true);
      }
    };

    const handleDecline = () => {
      if (sent) return;
      onDecline?.(confirm!, { confirmed: false });
      setSelection('declined');
      setSent(true);
      setCollapsed(true);
    };

    return (
      <div className={cls}>
        <div className="ma-msg">
          <div className="ma-msg-head">
            <div className="ma-left">
              <span className={`ma-icon ${category}`}><Icon size={16} /></span>
              <div className="ma-muted">[{label}] {ts}</div>
            </div>
            <div className="ma-right">
              {stats?.show && (
                <div className="ma-stats ma-stats-head">
                  {stats.model && (
                    <span className="ma-chip" title="模型/Agent">
                      <Cpu size={12} />
                      <span className="ma-chip-text">{stats.model}</span>
                    </span>
                  )}
                  <span className="ma-chip" title="调用次数">
                    <Hash size={12} />
                    <span className="ma-chip-text">{stats.calls}</span>
                  </span>
                  <span className="ma-chip" title="输入 tokens">
                    <LogIn size={12} />
                    <span className="ma-chip-text">{stats.inputTokens}</span>
                  </span>
                  <span className="ma-chip" title="输出 tokens">
                    <LogOut size={12} />
                    <span className="ma-chip-text">{stats.outputTokens}</span>
                  </span>
                </div>
              )}
              <button className="ma-linkbtn" onClick={() => setCollapsed((v) => !v)}>{collapsed ? '展开' : '折叠'}</button>
            </div>
          </div>
          {!collapsed && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <strong>{title}</strong>
            <span className="ma-muted">step: {confirm?.step_id}</span>
          </div>
          )}
          {!collapsed && planSummary && <div className="ma-muted" style={{ marginTop: 4 }}>{planSummary}</div>}
          {!collapsed && hasEditable ? (
            <>
              <div className="ma-toolbar">
                <div className="ma-muted">共有 {formTasks.length} 个任务</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="ma-linkbtn" onClick={() => { setEditMode('form'); setJson(JSON.stringify(formTasks, null, 2)); }}>表单编辑</button>
                  <button className="ma-linkbtn" onClick={() => { setEditMode('json'); setJson(JSON.stringify(formTasks, null, 2)); }}>编辑 JSON</button>
                </div>
              </div>
              {editMode === 'json' ? (
                <>
                  <div className="ma-muted" style={{ marginTop: 8 }}>编辑 JSON 以修改任务：</div>
                  <textarea className="ma-json" value={json} onChange={(e) => setJson(e.target.value)} />
                  {err && <div style={{ color: '#ef4444' }}>{err}</div>}
                </>
              ) : (
                <div className="ma-tasklist">
                  {formTasks.map((t, idx) => (
                    <div className="ma-task" key={idx}>
                      <div className="ma-task-head">#{idx + 1} {(t?.title || t?.name || `任务 ${idx + 1}`)}</div>
                      <div className="ma-form">
                        <div className="ma-field">
                          <label className="ma-label">标题（title）</label>
                          <input className="ma-inputbox" value={t?.title || ''} onChange={(e) => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, title: e.target.value } : x))} />
                        </div>
                        <div className="ma-field">
                          <label className="ma-label">目标（objective）</label>
                          <textarea className="ma-inputbox" value={t?.objective || ''} onChange={(e) => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, objective: e.target.value } : x))} />
                        </div>
                        <div className="ma-field">
                          <label className="ma-label">备注（notes）</label>
                          <input className="ma-inputbox" value={t?.notes || ''} onChange={(e) => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, notes: e.target.value } : x))} />
                        </div>
                        <div className="ma-field">
                          <label className="ma-label">提示（insights）</label>
                          <div className="ma-form">
                            {Array.isArray(t?.insights) && t.insights.length > 0 ? t.insights.map((it: any, j: number) => (
                              <div className="ma-inputrow" key={j}>
                                <input className="ma-inputbox" value={String(it)} onChange={(e) => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, insights: x.insights.map((s: any, k: number) => k === j ? e.target.value : s) } : x))} />
                                <button className="ma-mini" onClick={() => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, insights: x.insights.filter((_: any, k: number) => k !== j) } : x))}>删除</button>
                              </div>
                            )) : <div className="ma-muted">暂无</div>}
                            <button className="ma-mini" onClick={() => setFormTasks((arr) => arr.map((x, i) => i === idx ? { ...x, insights: Array.isArray(x.insights) ? [...x.insights, ''] : [''] } : x))}>新增</button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : !collapsed ? (
            <div className="ma-muted" style={{ marginTop: 8 }}>是否继续执行？</div>
          ) : (
            <div className="ma-muted ma-preview">
              {selection === 'confirmed' ? '已确认。' : selection === 'declined' ? '已取消。' : `需要确认（${title}）。点击“展开”查看详细。`}
            </div>
          )}
          {!collapsed && (
          <div className="ma-row" style={{ marginTop: 8 }}>
            <button className="ma-btn" disabled={sent} onClick={handleDecline}>取消</button>
            <button className="ma-btn" disabled={sent} onClick={handleConfirm}>确认</button>
          </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={cls}>
      <div className="ma-msg">
        <div className="ma-msg-head">
          <div className="ma-left">
            <span className={`ma-icon ${category}`}><Icon size={16} /></span>
            <div className="ma-muted">[{label}] {ts}</div>
          </div>
          <div className="ma-right">
            {stats?.show && (
              <div className="ma-stats ma-stats-head">
                {stats.model && (
                  <span className="ma-chip" title="模型/Agent">
                    <Cpu size={12} />
                    <span className="ma-chip-text">{stats.model}</span>
                  </span>
                )}
                <span className="ma-chip" title="调用次数">
                  <Hash size={12} />
                  <span className="ma-chip-text">{stats.calls}</span>
                </span>
                <span className="ma-chip" title="输入 tokens">
                  <LogIn size={12} />
                  <span className="ma-chip-text">{stats.inputTokens}</span>
                </span>
                <span className="ma-chip" title="输出 tokens">
                  <LogOut size={12} />
                  <span className="ma-chip-text">{stats.outputTokens}</span>
                </span>
              </div>
            )}
            <button className="ma-linkbtn" onClick={() => setCollapsed((v) => !v)}>{collapsed ? '展开' : '折叠'}</button>
          </div>
        </div>
        {collapsed ? (
          <div className="ma-muted ma-preview">{preview}</div>
        ) : (
          <div>{body}</div>
        )}
      </div>
    </div>
  );
}

type Category = 'user' | 'agent' | 'system' | 'plan' | 'solver' | 'aggregate' | 'pipeline';

function getCategory(event: string): Category {
  if (event.startsWith('user.')) return 'user';
  if (event.startsWith('agent.')) return 'agent';
  if (event.startsWith('plan.')) return 'plan';
  if (event.startsWith('solver.')) return 'solver';
  if (event.startsWith('aggregate.')) return 'aggregate';
  if (event === 'pipeline.completed' || event.startsWith('pipeline.')) return 'pipeline';
  if (event.startsWith('system.')) return 'system';
  return 'system';
}

function getIcon(cat: Category): LucideIcon {
  switch (cat) {
    case 'user': return User;
    case 'agent': return Bot;
    case 'system': return Settings;
    case 'plan': return ListTodo;
    case 'solver': return Wrench;
    case 'aggregate': return Puzzle;
    case 'pipeline': return GitMerge;
    default: return Settings;
  }
}

// Compute statistics summary for supported events
function computeStats(m: WebSocketMessage): {
  show: boolean;
  model?: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
} | null {
  const ev = String(m.event || '');
  try {
    let statsList: any[] | undefined;
    let model: string | undefined;
    let agentName: string | undefined;
    if (ev === 'plan.completed' || ev.endsWith('plan.completed')) {
      const c: any = (m as any).content;
      if (Array.isArray(c?.statistics)) statsList = c.statistics;
      // track agent name set
      if (statsList && statsList.length > 0) {
        const agents = Array.from(new Set(statsList.map((x) => x?.agent).filter(Boolean)));
        agentName = agents.length === 1 ? String(agents[0]) : undefined;
      }
    } else if (ev === 'solver.completed' || ev.endsWith('solver.completed')) {
      const c: any = (m as any).content;
      const res: any = c?.result;
      if (Array.isArray(res?.statistics)) statsList = res.statistics;
      agentName = typeof res?.agent_name === 'string' ? res.agent_name : undefined;
      // Prefer server-provided model on result
      if (typeof res?.model === 'string' && res.model) {
        model = res.model;
      }
    } else {
      return null;
    }
    if (!statsList || statsList.length === 0) {
      // Fallback: if solver.completed carries model but no per-call stats,
      // still display the model chip with zeros.
      if ((ev === 'solver.completed' || ev.endsWith('solver.completed')) && model) {
        return { show: true, model, calls: 0, inputTokens: 0, outputTokens: 0 };
      }
      return null;
    }
    // Prefer model from per-call entries
    const models = Array.from(
      new Set(
        statsList
          .map((x) => x?.model || x?.metadata?.model)
          .filter((v: any) => typeof v === 'string' && v)
      )
    );
    if (!model) {
      if (models.length === 1) {
        model = String(models[0]);
      } else if (models.length > 1) {
        model = models.join(', ');
      }
    }
    // Fallback for plan.completed: try metrics snapshot mapping by agent
    if (!model && (ev === 'plan.completed' || ev.endsWith('plan.completed'))) {
      const c: any = (m as any).content;
      const metrics = c?.metrics;
      const byAgent = metrics?.models?.by_agent;
      const agentMap = agentName && byAgent ? byAgent[agentName] : undefined;
      if (agentMap && typeof agentMap === 'object') {
        const keys = Object.keys(agentMap);
        if (keys.length === 1) model = keys[0];
        else if (keys.length > 1) model = keys.join(', ');
      }
    }
    let input = 0;
    let output = 0;
    for (const it of statsList) {
      const i = Number(it?.input_tokens ?? 0);
      const o = Number(it?.output_tokens ?? 0);
      if (Number.isFinite(i)) input += i;
      if (Number.isFinite(o)) output += o;
    }
    return {
      show: true,
      model,
      calls: statsList.length,
      inputTokens: input,
      outputTokens: output,
    };
  } catch {
    return null;
  }
}
