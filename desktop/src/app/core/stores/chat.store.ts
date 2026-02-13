import { Injectable, signal } from "@angular/core";
import { ChatMessage, ChatAuthor } from "../models/chat.model";
import { firstValueFrom } from "rxjs";
import { LlmClient } from "../services/clients/llm.client";
import { SettingsStore } from "./settings.store";

function uid() {
  return crypto.randomUUID();
}

@Injectable({ providedIn: "root" })
export class ChatStore {
  readonly messages = signal<ChatMessage[]>([]);

  constructor(
    private readonly llm: LlmClient,
    private readonly settings: SettingsStore,
  ) {}

  add(author: ChatAuthor, text: string) {
    const msg: ChatMessage = {
      id: uid(),
      author,
      text,
      createdAt: Date.now(),
      favorite: false,
      status: "final",
    };
    this.messages.update(list => [...list, msg]);
    return msg.id;
  }

  // --- helpers para STT (system) ---
  addSystemStreaming(text: string, sessionId?: string | null): string {
    const id = this.add("system" as any, text); // si ChatAuthor ya tiene "system", quita "as any"
    this.messages.update(list =>
      list.map(m => (m.id === id ? { ...m, sessionId: sessionId ?? null, status: "streaming" } : m))
    );
    return id;
  }

  addSystemFinal(text: string, sessionId?: string | null): string {
    const id = this.add("system" as any, text);
    this.messages.update(list =>
      list.map(m => (m.id === id ? { ...m, sessionId: sessionId ?? null, status: "final" } : m))
    );
    return id;
  }

  finalizeSystem(id: string, finalText: string) {
    this.updateText(id, finalText, "final");
  }

  addSystemError(message: string, sessionId?: string | null): string {
    const id = this.add("system" as any, message);
    this.messages.update(list =>
      list.map(m => (m.id === id ? { ...m, sessionId: sessionId ?? null, status: "error" } : m))
    );
    return id;
  }

  updateText(id: string, text: string, status: ChatMessage["status"] = "final") {
    this.messages.update(list =>
      list.map(m => (m.id === id ? { ...m, text, status } : m))
    );
  }

  toggleFavorite(id: string) {
    this.messages.update(list =>
      list.map(m => (m.id === id ? { ...m, favorite: !m.favorite } : m))
    );
  }

  async copy(id: string) {
    const msg = this.messages().find(m => m.id === id);
    if (!msg) return;
    await navigator.clipboard.writeText(msg.text ?? "");
  }

  async translate(id: string) {
    const msg = this.messages().find(m => m.id === id);
    if (!msg) return;

    const s = this.settings.settings();
    const targetLang = s.language?.appLanguage ?? "es";

    const outId = this.add("ai", "Traduciendo…");
    this.updateText(outId, "Traduciendo…", "streaming");

    try {
      const res = await firstValueFrom(
        this.llm.generate({
          provider: s.selectedLlmProviderId,
          temperature: 0.2,
          max_tokens: 256,
          config: this.pickLlmConfig(s),
          extra: null,
          messages: [
            { role: "system", content: `Traduce al idioma: ${targetLang}. Solo devuelve la traducción.` },
            { role: "user", content: msg.text },
          ],
        })
      );
      this.updateText(outId, res.text ?? "(vacío)", "final");
    } catch (e: any) {
      this.updateText(outId, e?.message ?? "Error traduciendo", "error");
    }
  }

  async generateFromSystem(systemMsgId: string) {
    const sys = this.messages().find(m => m.id === systemMsgId);
    if (!sys) return;

    const s = this.settings.settings();
    const outId = this.add("ai", "Generando respuesta IA…");
    this.updateText(outId, "Generando respuesta IA…", "streaming");

    try {
      const res = await firstValueFrom(
        this.llm.generate({
          provider: s.selectedLlmProviderId,
          temperature: s.llm.temperature,
          max_tokens: s.llm.maxTokens,
          config: this.pickLlmConfig(s),
          extra: null,
          messages: [{ role: "user", content: sys.text }],
        })
      );
      this.updateText(outId, res.text ?? "(vacío)", "final");
    } catch (e: any) {
      this.updateText(outId, e?.message ?? "Error generando", "error");
    }
  }

  forwardToTeleprompter(id: string) {
    const msg = this.messages().find(m => m.id === id);
    if (!msg) return;
    // TODO: conectar con OverlayStore/TeleprompterService
    console.log("FORWARD to teleprompter:", msg.text);
  }

  private pickLlmConfig(s: any): Record<string, unknown> {
    if (s.selectedLlmProviderId === "gemini") {
      return {
        api_key: s.llm.gemini.apiKey,
        model: s.llm.gemini.model,
        timeout_s: Math.floor(s.llm.gemini.timeoutMs / 1000),
      };
    }
    return {
      api_key: s.llm.openaiCompat.apiKey,
      model: s.llm.openaiCompat.model,
      timeout_s: Math.floor(s.llm.openaiCompat.timeoutMs / 1000),
    };
  }


}
