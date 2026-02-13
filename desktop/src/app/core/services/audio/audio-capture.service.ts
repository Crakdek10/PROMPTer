import { Injectable } from "@angular/core";

type OnChunk = (pcm16: Int16Array, sampleRate: number) => void;
export type CaptureMode = "mic" | "system" | "both";

@Injectable({ providedIn: "root" })
export class AudioCaptureService {
  private stream: MediaStream | null = null;
  private ctx: AudioContext | null = null;
  private src: MediaStreamAudioSourceNode | null = null;
  private node: AudioWorkletNode | null = null;
  private zero: GainNode | null = null;

  // "both"
  private micStream: MediaStream | null = null;
  private sysStream: MediaStream | null = null;
  private micSrc: MediaStreamAudioSourceNode | null = null;
  private sysSrc: MediaStreamAudioSourceNode | null = null;
  private mix: GainNode | null = null;

  async start(
    onChunk: OnChunk,
    targetSampleRate = 16000,
    opts: { mode?: CaptureMode; systemSourceId?: string } = {}
  ) {
    await this.stop();

    const mode: CaptureMode = opts.mode ?? "mic";

    // 1) AudioContext
    this.ctx = new AudioContext();
    if (this.ctx.state === "suspended") await this.ctx.resume();

    // 2) Worklet
    await this.ctx.audioWorklet.addModule("/audio/pcm16-downsampler.worklet.js");

    // 3) WorkletNode
    this.node = new AudioWorkletNode(this.ctx, "pcm16-downsampler", {
      processorOptions: {
        targetSampleRate,
        chunkSize: 2048,
      },
      numberOfInputs: 1,
      numberOfOutputs: 1,
      channelCount: 1,
    });

    // 4) Grafo silencioso
    this.zero = this.ctx.createGain();
    this.zero.gain.value = 0;

    this.node.connect(this.zero);
    this.zero.connect(this.ctx.destination);

    // 5) Fuente
    if (mode === "mic") {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.src = this.ctx.createMediaStreamSource(this.stream);
      this.src.connect(this.node);
    }

    if (mode === "system") {
      const systemSourceId = opts.systemSourceId;
      if (!systemSourceId) throw new Error("Falta systemSourceId (desktopCapturer source id)");

      // Electron desktop capture (a veces requiere video aunque no lo uses)
      const constraints: any = {
        audio: {
          mandatory: {
            chromeMediaSource: "desktop",
            chromeMediaSourceId: systemSourceId,
          },
        },
        video: {
          mandatory: {
            chromeMediaSource: "desktop",
            chromeMediaSourceId: systemSourceId,
          },
        },
      };

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.src = this.ctx.createMediaStreamSource(this.stream);
      this.src.connect(this.node);
    }

    if (mode === "both") {
      const systemSourceId = opts.systemSourceId;
      if (!systemSourceId) throw new Error("Falta systemSourceId para modo both");

      const sysConstraints: any = {
        audio: {
          mandatory: {
            chromeMediaSource: "desktop",
            chromeMediaSourceId: systemSourceId,
          },
        },
        video: {
          mandatory: {
            chromeMediaSource: "desktop",
            chromeMediaSourceId: systemSourceId,
          },
        },
      };

      this.micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.sysStream = await navigator.mediaDevices.getUserMedia(sysConstraints);

      this.micSrc = this.ctx.createMediaStreamSource(this.micStream);
      this.sysSrc = this.ctx.createMediaStreamSource(this.sysStream);

      this.mix = this.ctx.createGain();
      this.mix.gain.value = 1.0;

      this.micSrc.connect(this.mix);
      this.sysSrc.connect(this.mix);
      this.mix.connect(this.node);
    }

    // 6) chunks desde worklet
    this.node.port.onmessage = (ev: MessageEvent) => {
      const msg = ev.data;
      if (!msg || msg.type !== "chunk") return;

      const samples = Number(msg.samples || 0);
      const sr = Number(msg.sampleRate || targetSampleRate);

      const pcm16 = new Int16Array(msg.pcm16 as ArrayBuffer);
      const sliced = samples > 0 && samples < pcm16.length ? pcm16.slice(0, samples) : pcm16;

      onChunk(sliced, sr);
    };
  }

  async stop() {
    try { this.node?.disconnect(); } catch {}
    try { this.src?.disconnect(); } catch {}
    try { this.zero?.disconnect(); } catch {}

    try { this.micSrc?.disconnect(); } catch {}
    try { this.sysSrc?.disconnect(); } catch {}
    try { this.mix?.disconnect(); } catch {}

    this.node = null;
    this.src = null;
    this.zero = null;

    this.micSrc = null;
    this.sysSrc = null;
    this.mix = null;

    if (this.ctx) {
      try { await this.ctx.close(); } catch {}
      this.ctx = null;
    }

    if (this.stream) {
      for (const t of this.stream.getTracks()) t.stop();
      this.stream = null;
    }
    if (this.micStream) {
      for (const t of this.micStream.getTracks()) t.stop();
      this.micStream = null;
    }
    if (this.sysStream) {
      for (const t of this.sysStream.getTracks()) t.stop();
      this.sysStream = null;
    }
  }
}
