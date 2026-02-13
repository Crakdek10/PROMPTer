import { Injectable, inject } from "@angular/core";
import { SttWsClient } from "./clients/stt.ws.client";

@Injectable({ providedIn: "root" })
export class SttService {
  private readonly ws = inject(SttWsClient);

  readonly messages$ = this.ws.messages$;
  readonly status$ = this.ws.status$;

  async connect(): Promise<void> {
    await this.ws.connectAsync(6000);
  }

  start(
    sessionId: string,
    sttConfig: { provider?: string; language?: string; sample_rate?: number; format?: string } = {}
  ): void {
    const config: Record<string, unknown> = {
      provider: sttConfig.provider ?? "cloud_stub",
      language: sttConfig.language ?? "es",
      sample_rate: sttConfig.sample_rate ?? 16000,
      format: sttConfig.format ?? "pcm16",
      partial_every_s: 1.5,
      partial_min_audio_s: 1.0,
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
