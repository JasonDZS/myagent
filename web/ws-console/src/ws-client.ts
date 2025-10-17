import { WebSocketMessage } from './types';

type Listener = (m: WebSocketMessage) => void;

export interface AgentWSClientOptions {
  url: string;
  token?: string;
  autoReconnect?: boolean;
  ackIntervalMs?: number; // 200ms default
  onOpen?: () => void;
  onClose?: (ev?: any) => void;
  onError?: (err: any) => void;
}

export class AgentWSClient {
  private ws: WebSocket | null = null;
  private opts: AgentWSClientOptions;
  private listeners: Set<Listener> = new Set();
  private reconnectTimer: any = null;
  private lastEventId: string | null = null;
  private lastSeq: number = 0;
  private ackTimer: any = null;
  private connected: boolean = false;

  constructor(opts: AgentWSClientOptions) {
    this.opts = { autoReconnect: true, ackIntervalMs: 200, ...opts };
  }

  isOpen(): boolean {
    return this.connected && !!this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  getLastEvent(): { lastEventId: string | null; lastSeq: number } {
    return { lastEventId: this.lastEventId, lastSeq: this.lastSeq };
  }

  onMessage(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const url = this.buildUrlWithToken();
      this.ws = new WebSocket(url);
      this.connected = false;

      this.ws.onopen = () => {
        this.connected = true;
        this.startAckLoop();
        this.opts.onOpen?.();
      };

      this.ws.onclose = (ev) => {
        this.connected = false;
        this.stopAckLoop();
        this.opts.onClose?.(ev);
        if (this.opts.autoReconnect) this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        this.opts.onError?.(err);
      };

      this.ws.onmessage = (e) => {
        try {
          const m = JSON.parse(e.data) as WebSocketMessage;
          if (typeof m.event_id === 'string') this.lastEventId = m.event_id;
          if (typeof (m as any).seq === 'number') this.lastSeq = (m as any).seq as number;
          this.listeners.forEach((fn) => fn(m));
        } catch (err) {
          console.warn('Invalid WS message', err);
        }
      };
    } catch (err) {
      this.opts.onError?.(err);
      if (this.opts.autoReconnect) this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.opts.autoReconnect = false;
    this.stopAckLoop();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    try {
      this.ws?.close();
    } catch {}
    this.ws = null;
    this.connected = false;
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 1000);
  }

  private startAckLoop() {
    this.stopAckLoop();
    const interval = this.opts.ackIntervalMs ?? 200;
    this.ackTimer = setInterval(() => {
      if (!this.isOpen()) return;
      const content = this.lastEventId
        ? { last_event_id: this.lastEventId }
        : { last_seq: this.lastSeq };
      this.send({ event: 'user.ack', content });
    }, interval);
  }

  private stopAckLoop() {
    if (this.ackTimer) clearInterval(this.ackTimer);
    this.ackTimer = null;
  }

  private buildUrlWithToken(): string {
    if (!this.opts.token) return this.opts.url;
    try {
      const u = new URL(this.opts.url);
      u.searchParams.set('token', this.opts.token);
      return u.toString();
    } catch {
      // if invalid URL, best effort append
      const sep = this.opts.url.includes('?') ? '&' : '?';
      return `${this.opts.url}${sep}token=${encodeURIComponent(this.opts.token!)}`;
    }
  }

  send(payload: any): void {
    if (!this.ws) return;
    try {
      this.ws.send(JSON.stringify({ ...payload, timestamp: new Date().toISOString() }));
    } catch (err) {
      this.opts.onError?.(err);
    }
  }
}

