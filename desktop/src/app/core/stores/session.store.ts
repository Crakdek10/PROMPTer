import { patchState, signalStore, withMethods, withState } from "@ngrx/signals";
import { inject } from "@angular/core";
import { AudioCaptureService, CaptureMode } from "../services/audio/audio-capture.service";
import { SttService } from "../services/stt.service";
import { pcm16ToBase64 } from "../utils/audio-b64";
import { SettingsStore } from "./settings.store";
import { ChatStore } from "./chat.store";

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

        // --- modo captura ---
        const mode: CaptureMode = (s?.sttUi?.captureMode ?? "mic") as CaptureMode;
        const systemSourceId: string | null = s?.sttUi?.selectedSystemSourceId ?? null;

        // Si pide system/both pero no eligió fuente
        if ((mode === "system" || mode === "both") && !systemSourceId) {
          const id = chat.addSystemError("Elige una fuente de audio del sistema en Settings.");
          patchState(store, { status: "idle", sessionId: null, systemMsgId: null });
          return;
        }

        // 1) conectar WS
        await stt.connect();

        const sessionId = uid();
        patchState(store, { status: "recording", sessionId });

        // 2) start STT
        stt.start(sessionId, {
          provider: s?.stt?.provider ?? "whisper_selfhosted",
          language: s?.language?.appLanguage ?? "es",
          sample_rate: 16000,
          format: "pcm16",
        });


        // 5) start captura
        await audio.start(
          (pcm16, sr) => {
            const b64 = pcm16ToBase64(pcm16);
            stt.sendAudioChunk(b64, sr);
          },
          16000,
          { mode, systemSourceId: systemSourceId ?? undefined }
        );

        // 3) mensaje streaming en chat
        const systemMsgId = chat.addSystemStreaming("Escuchando…", sessionId);
        patchState(store, { systemMsgId });

        // 4) escuchar mensajes WS
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

      },

      async stopSession() {
        if (store.status() !== "recording") return;

        patchState(store, { status: "processing" });

        // stop captura
        await audio.stop();

        // stop STT (el backend cerrará WS luego del final)
        stt.stop();
      },

      setProcessing() {
        patchState(store, { status: "processing" });
      },
    };
  })
);
