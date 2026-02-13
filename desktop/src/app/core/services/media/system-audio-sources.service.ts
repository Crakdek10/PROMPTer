import { Injectable } from "@angular/core";

@Injectable({ providedIn: "root" })
export class SystemAudioSourcesService {
  async list() {
    if (!window.prompter?.listSystemAudioSources) return [];
    return await window.prompter.listSystemAudioSources();
  }
}
