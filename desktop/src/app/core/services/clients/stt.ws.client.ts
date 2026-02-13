import { Injectable, inject } from "@angular/core";
import { Subject, Observable } from "rxjs";
import { RuntimeConfigService } from "../runtime/runtime-config.service";
import {
  ClientStart,
  ClientAudio,
  ClientStop,
  ClientMessage,
  ServerMessage,
} from "../../models/stt-ws.model";

@Injectable({ providedIn: "root" })
export class SttWsClient {
  private readonly runtime = inject(RuntimeConfigService);

  private ws: WebSocket | null = null;

  private readonly _messages$ = new Subject<ServerMessage>();
  public readonly messages$: Observable<ServerMessage> = this._messages$.asObservable();

  private readonly _status$ = new Subject<"disconnected" | "connecting" | "connected">();
  public readonly status$ = this._status$.asObservable();

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this._status$.next("connecting");
    const base = (this.runtime.wsBaseUrl() || "").replace(/\/+$/, "");
    this.ws = new WebSocket(`${base}/ws/stt`);


    this.ws.onopen = () => this._status$.next("connected");

    this.ws.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data) as ServerMessage;
        if (!parsed || typeof parsed !== "object" || !("type" in parsed)) {
          this._messages$.next({ type: "error", message: "Invalid server message" });
          return;
        }
        this._messages$.next(parsed);
      } catch {
        this._messages$.next({ type: "error", message: "Invalid JSON from server" });
      }
    };

    this.ws.onerror = () => {
      this._messages$.next({ type: "error", message: "WebSocket error" });
    };

    this.ws.onclose = () => {
      this._status$.next("disconnected");
      this.ws = null;
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._status$.next("disconnected");
  }

  send(msg: ClientMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this._messages$.next({ type: "error", message: "WS not connected" });
      return;
    }
    this.ws.send(JSON.stringify(msg));
  }

  start(sessionId: string, config?: Record<string, unknown>): void {
    const msg: ClientStart = { type: "start", session_id: sessionId };
    if (config) msg.config = config;
    this.send(msg);
  }

  audio(format: ClientAudio["format"], sampleRate: number, dataB64: string): void {
    const msg: ClientAudio = { type: "audio", format, sample_rate: sampleRate, data: dataB64 };
    this.send(msg);
  }

  stop(): void {
    const msg: ClientStop = { type: "stop" };
    this.send(msg);
  }
}
