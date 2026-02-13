import { Injectable, inject } from "@angular/core";
import { SttWsClient } from "./clients/stt.ws.client";

@Injectable({ providedIn: "root" })
export class SttService {
  private readonly ws = inject(SttWsClient);

  readonly messages$ = this.ws.messages$;

  async connect(): Promise<void> {
    await this.ws.connectAsync(6000);
  }

  start(
    sessionId: string,
    sttConfig: {
      provider?: string;
      language?: string;
      sample_rate?: number;
      format?: string;
      partial_every_s?: number;
      partial_window_s?: number;
      partial_min_window_s?: number;
    } = {}
  ): void {
    const config: Record<string, unknown> = {
      provider: sttConfig.provider ?? "whisper_selfhosted",
      language: sttConfig.language ?? "es",
      sample_rate: sttConfig.sample_rate ?? 16000,
      format: sttConfig.format ?? "pcm16",

      partial_every_s: sttConfig.partial_every_s ?? 1.6,
      partial_window_s: sttConfig.partial_window_s ?? 6.0,
      partial_min_window_s: sttConfig.partial_min_window_s ?? 2.0,
    };


    this.ws.start(sessionId, config);
  }

  sendAudioChunk(dataB64: string, sampleRate = 16000): void {
    this.ws.audio("pcm16", sampleRate, dataB64);
  }

  stop(): void {
    this.ws.stop();
  }

  disconnect(): void {
    this.ws.disconnect();
  }
}
