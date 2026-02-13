import { Injectable, inject } from "@angular/core";
import { SettingsStore } from "../stores/settings.store";
import { SessionStore } from "../stores/session.store";
import { ChatStore } from "../stores/chat.store";
import { pcm16ToBase64 } from "../utils/audio-b64";
import { filter, firstValueFrom } from "rxjs";
import { AudioCaptureService } from "../services/audio/audio-capture.service";
import { SttWsClient } from "../services/clients/stt.ws.client";

@Injectable({ providedIn: "root" })
export class SessionController {
  private settings = inject(SettingsStore);
  private session = inject(SessionStore);
  private chat = inject(ChatStore);
  private audio = inject(AudioCaptureService);
  private sttWs = inject(SttWsClient);

  private sessionId: string | null = null;
  private streamingMsgId: string | null = null;
  private audioRunning = false;

  constructor() {
    this.sttWs.messages$.subscribe(m => this.onSttMsg(m));

    this.sttWs.status$.subscribe(status => {
      if (status === "disconnected" && this.session.status() !== "idle") {
        this.forceStop();
      }
    });
  }

  togglePlay() {
    if (this.session.status() === "recording") return this.stop();
    return this.start();
  }

  async start() {
    const s = this.settings.settings();

    this.sessionId = crypto.randomUUID?.() ?? String(Date.now());
    this.audioRunning = false;
    this.streamingMsgId = null;

    this.session.startSession();

    this.sttWs.connect();

    await firstValueFrom(this.sttWs.status$.pipe(filter(x => x === "connected")));

    const sttConfig: Record<string, unknown> = {
      provider: s.selectedSttProviderId,
      sample_rate: s.stt.sampleRate,
      format: s.stt.format,
      language: s.stt.language ?? "en",
    };

    this.sttWs.start(this.sessionId, sttConfig);
  }

  stop() {
    if (this.session.status() !== "recording") return;
    this.session.setProcessing(); // Cambia a "Generando respuesta..."

    try { this.audio.stop(); } catch {}
    try { this.sttWs.stop(); } catch {}
  }

  // Helper para resetear toda la UI y la captura de forma segura
  private forceStop() {
    this.audioRunning = false;
    this.streamingMsgId = null;
    try { this.audio.stop(); } catch {}
    this.session.stopSession();
  }

  private async startAudioIfNeeded(sampleRate: number) {
    if (this.audioRunning) return;
    this.audioRunning = true;

    await this.audio.start((pcm16, sr) => {
      if (!this.sessionId) return;
      this.sttWs.audio("pcm16", sr, pcm16ToBase64(pcm16));
    }, sampleRate);
  }

  private onSttMsg(m: any) {
    if (m.session_id && m.session_id !== this.sessionId) return;

    if (m.type === "ready") {
      const s = this.settings.settings();
      this.startAudioIfNeeded(s.stt.sampleRate);
      return;
    }

    if (m.type === "partial") {
      if (!this.streamingMsgId) {
        this.streamingMsgId = this.chat.addSystemStreaming(m.text, this.sessionId);
      } else {
        this.chat.updateText(this.streamingMsgId, m.text, "streaming");
      }
      return;
    }

    if (m.type === "final") {
      if (!this.streamingMsgId) {
        this.chat.addSystemFinal(m.text, this.sessionId);
      } else {
        this.chat.updateText(this.streamingMsgId, m.text, "final");
      }
      this.forceStop();
      return;
    }

    if (m.type === "error") {
      this.chat.addSystemError(`❌ ${m.message ?? "STT error"}`, this.sessionId);
      this.forceStop();
    }
  }
}
