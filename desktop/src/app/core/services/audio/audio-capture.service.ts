import { Injectable } from "@angular/core";

type OnChunk = (pcm16: Int16Array, sampleRate: number) => void;

@Injectable({ providedIn: "root" })
export class AudioCaptureService {
  private stream: MediaStream | null = null;
  private ctx: AudioContext | null = null;
  private src: MediaStreamAudioSourceNode | null = null;
  private node: AudioWorkletNode | null = null;
  private zero: GainNode | null = null;

  async start(onChunk: OnChunk, targetSampleRate = 16000) {
    await this.stop();

    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // El sampleRate real lo decide el browser; el worklet lo baja a targetSampleRate.
    this.ctx = new AudioContext();
    if (this.ctx.state === "suspended") await this.ctx.resume();

    // Carga del worklet desde assets (Angular dev + prod lo sirven)
    await this.ctx.audioWorklet.addModule("/audio/pcm16-downsampler.worklet.js");

    this.src = this.ctx.createMediaStreamSource(this.stream);

    this.node = new AudioWorkletNode(this.ctx, "pcm16-downsampler", {
      processorOptions: {
        targetSampleRate,
        chunkSize: 2048, // ajusta: 1024 más “rápido”, 4096 más “suave”
      },
      numberOfInputs: 1,
      numberOfOutputs: 1,
      channelCount: 1,
    });

    // 🔇 evitar eco: conectar a gain 0 -> destination (para que el grafo "corra")
    this.zero = this.ctx.createGain();
    this.zero.gain.value = 0;

    this.src.connect(this.node);
    this.node.connect(this.zero);
    this.zero.connect(this.ctx.destination);

    this.node.port.onmessage = (ev: MessageEvent) => {
      const msg = ev.data;
      if (!msg || msg.type !== "chunk") return;

      const samples = Number(msg.samples || 0);
      const sr = Number(msg.sampleRate || targetSampleRate);

      // pcm16 es ArrayBuffer transferido
      const pcm16 = new Int16Array(msg.pcm16 as ArrayBuffer);

      // recorta al tamaño real (por si el buffer es chunkSize pero no lleno)
      const sliced = samples > 0 && samples < pcm16.length ? pcm16.slice(0, samples) : pcm16;

      onChunk(sliced, sr);
    };
  }

  async stop() {
    try { this.node?.disconnect(); } catch {}
    try { this.src?.disconnect(); } catch {}
    try { this.zero?.disconnect(); } catch {}

    this.node = null;
    this.src = null;
    this.zero = null;

    if (this.ctx) {
      try { await this.ctx.close(); } catch {}
      this.ctx = null;
    }

    if (this.stream) {
      for (const t of this.stream.getTracks()) t.stop();
      this.stream = null;
    }
  }
}
