import { Injectable, inject } from "@angular/core";
import { SettingsStore } from "../stores/settings.store";
import { SessionStore } from "../stores/session.store";
import { ChatStore } from "../stores/chat.store";
import { pcm16ToBase64 } from "../utils/audio-b64";
import { filter, firstValueFrom } from "rxjs";
import {AudioCaptureService} from '../services/audio/audio-capture.service';
import {SttWsClient} from '../services/clients/stt.ws.client';

@Injectable({ providedIn: "root" })
export class SessionController {
  private settings = inject(SettingsStore);
  private session = inject(SessionStore);
  private chat = inject(ChatStore);
  private audio = inject(AudioCaptureService);
  private sttWs = inject(SttWsClient);

  private sessionId: string | null = null;
  private streamingMsgId: string | null = null;

  constructor() {
    this.sttWs.messages$.subscribe(m => this.onSttMsg(m));
  }

  togglePlay() {
    if (this.session.status() === "recording") return this.stop();
    return this.start();
  }

  async start() {
    const s = this.settings.settings();
    this.session.startSession();

    this.sessionId = crypto.randomUUID?.() ?? String(Date.now());

    // 1) connect WS (usa runtime.wsBaseUrl interno)
    this.sttWs.connect();

    // 2) esperar connected
    await firstValueFrom(this.sttWs.status$.pipe(filter(x => x === "connected")));

    // 3) start
    this.sttWs.start(this.sessionId, {
      provider: s.selectedSttProviderId,
      sample_rate: s.stt.sampleRate,
      format: s.stt.format,
      // luego: model / base_url / etc
    });

    // 4) audio streaming
    await this.audio.start((pcm16, sr) => {
      if (!this.sessionId) return;
      this.sttWs.audio("pcm16", sr, pcm16ToBase64(pcm16));
    }, s.stt.sampleRate);
  }

  stop() {
    if (this.session.status() !== "recording") return;
    this.session.setProcessing();
    try { this.audio.stop(); } catch {}
    try { this.sttWs.stop(); } catch {}
  }

  private onSttMsg(m: any) {
    if (m.type === "ready") return;

    if (m.type === "partial") {
      // crea o actualiza burbuja system streaming
      if (!this.streamingMsgId) {
        this.streamingMsgId = this.chat.addSystemStreaming(m.text, this.sessionId);
      } else {
        this.chat.updateText(this.streamingMsgId, m.text);
      }
      return;
    }

    if (m.type === "final") {
      if (!this.streamingMsgId) {
        this.chat.addSystemFinal(m.text, this.sessionId);
      } else {
        this.chat.finalizeSystem(this.streamingMsgId, m.text);
        this.streamingMsgId = null;
      }
      this.session.stopSession(); // vuelve a idle
      return;
    }

    if (m.type === "error") {
      this.chat.addSystemError(m.message ?? "STT error");
      this.session.stopSession();
    }
  }

}
