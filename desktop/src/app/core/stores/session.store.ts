import { patchState, signalStore, withMethods, withState } from "@ngrx/signals";
import { inject } from "@angular/core";
import { AudioCaptureService } from "../services/audio/audio-capture.service";
import { SttService } from "../services/stt.service";
import { SettingsStore } from "./settings.store";
import { ChatStore } from "./chat.store";
import { pcm16ToBase64 } from "../utils/audio-b64";

export type SessionStatus = "idle" | "recording" | "paused" | "processing";

type SessionState = {
  status: SessionStatus;
  sessionId: string | null;
  systemMsgId: string | null;
};

const initialState: SessionState = {
  status: "idle",
  sessionId: null,
  systemMsgId: null,
};

function uid() {
  return crypto.randomUUID();
}

export const SessionStore = signalStore(
  { providedIn: "root" },
  withState(initialState),
  withMethods((store) => {
    const stt = inject(SttService);
    const audio = inject(AudioCaptureService);
    const settings = inject(SettingsStore);
    const chat = inject(ChatStore);

    let sub: any = null;

    return {
      async startSession() {
        if (store.status() === "recording") return;

        const s: any = settings.settings();

        // SOLO SYSTEM AUDIO
        const systemSourceId: string | null = s?.sttUi?.selectedSystemSourceId ?? null;
        if (!systemSourceId) {
          chat.addSystemError("Elige una fuente de audio del sistema en Settings.");
          return;
        }

        // 1) conectar WS (espera OPEN)
        await stt.connect();

        const sessionId = uid();
        patchState(store, { status: "recording", sessionId });

        // 2) crear mensaje streaming ANTES para que existan updates desde ya
        const systemMsgId = chat.addSystemStreaming("Escuchando…", sessionId);
        patchState(store, { systemMsgId });

        // 3) subscribe WS ANTES de start (por si llega ready/partial rápido)
        sub = stt.messages$.subscribe((m: any) => {
          if (m.type === "partial") {
            chat.updateText(systemMsgId, m.text, "streaming");
          } else if (m.type === "final") {
            chat.finalizeSystem(systemMsgId, m.text);
            patchState(store, { status: "idle", sessionId: null, systemMsgId: null });
            stt.disconnect();
            try { sub?.unsubscribe?.(); } catch {}
            sub = null;
          } else if (m.type === "error") {
            chat.updateText(systemMsgId, m.message ?? "Error STT", "error");
            patchState(store, { status: "idle", sessionId: null, systemMsgId: null });
            stt.disconnect();
            try { sub?.unsubscribe?.(); } catch {}
            sub = null;
          }
        });

        // 4) start STT
        stt.start(sessionId, {
          provider: s?.stt?.provider ?? "whisper_selfhosted",
          language: s?.language?.appLanguage ?? "es",
          sample_rate: 16000,
          format: "pcm16",
        });

        // 5) función onChunk (envía audio a WS)
        const onChunk = (pcm16: Int16Array, sampleRate: number) => {
          if (store.status() !== "recording") return;
          const b64 = pcm16ToBase64(pcm16);
          stt.sendAudioChunk(b64, sampleRate);
        };

        // 6) start captura (SYSTEM)
        await audio.start(onChunk, 16000, { mode: "system", systemSourceId });
      },

      async stopSession() {
        if (store.status() !== "recording") return;

        patchState(store, { status: "processing" });

        // stop captura primero
        await audio.stop();

        // stop STT (backend mandará final y cerrará)
        stt.stop();
      },

      setProcessing() {
        patchState(store, { status: "processing" });
      },
    };
  })
);
