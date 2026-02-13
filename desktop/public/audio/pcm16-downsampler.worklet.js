/* eslint-disable no-undef */
// AudioWorkletProcessor que:
// - recibe Float32 (sampleRate nativo del AudioContext)
// - re-muestrea a targetSampleRate
// - convierte a PCM16
// - manda chunks por port.postMessage con ArrayBuffer transferible

class Pcm16DownsamplerProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();

    const opts = (options && options.processorOptions) || {};
    this.targetRate = Number(opts.targetSampleRate || 16000);
    this.chunkSize = Number(opts.chunkSize || 2048); // samples PCM16 por mensaje

    // ratio = inputRate / outputRate
    this.ratio = sampleRate / this.targetRate;
    this.pos = 0; // posición fraccional dentro del input (en samples)

    this.outIndex = 0;
    this.out = new Int16Array(this.chunkSize);
  }

  _emit() {
    // Enviamos SOLO los samples válidos (outIndex)
    const buf = this.out.buffer;

    this.port.postMessage(
      {
        type: "chunk",
        sampleRate: this.targetRate,
        samples: this.outIndex,
        pcm16: buf,
      },
      [buf]
    );

    // OJO: como transferimos buffer, debemos recrear
    this.out = new Int16Array(this.chunkSize);
    this.outIndex = 0;
  }

  process(inputs) {
    const input = inputs && inputs[0] && inputs[0][0];
    if (!input || input.length === 0) return true;

    const len = input.length;

    // Resample lineal usando this.pos (se conserva entre callbacks)
    while (this.pos < len - 1) {
      const i0 = this.pos | 0;
      const i1 = i0 + 1;
      const frac = this.pos - i0;

      const s = input[i0] * (1 - frac) + input[i1] * frac;

      // float [-1,1] -> int16
      const clamped = Math.max(-1, Math.min(1, s));
      const v = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;

      this.out[this.outIndex++] = v;

      if (this.outIndex >= this.chunkSize) this._emit();

      this.pos += this.ratio;
    }

    // mantener pos relativo al siguiente frame
    this.pos -= len;
    if (this.pos < 0) this.pos = 0;

    return true;
  }
}

registerProcessor("pcm16-downsampler", Pcm16DownsamplerProcessor);
