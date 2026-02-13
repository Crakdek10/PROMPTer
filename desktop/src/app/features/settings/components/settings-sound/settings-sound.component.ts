import { Component, OnInit, inject, signal } from "@angular/core";
import { SettingsStore } from "../../../../core/stores/settings.store";

type SystemSource = { id: string; name: string };
type MicDevice = { deviceId: string; label: string };

@Component({
  selector: "app-settings-sound",
  standalone: true,
  templateUrl: "./settings-sound.component.html",
})
export class SettingsSoundComponent implements OnInit {
  private readonly settings = inject(SettingsStore);

  readonly micDevices = signal<MicDevice[]>([]);
  readonly systemSources = signal<SystemSource[]>([]);

  get s() {
    return this.settings.settings();
  }

  get selectedMicId(): string {
    return this.s?.sttUi?.selectedMicId ?? "";
  }

  get selectedSystemSourceId(): string {
    return this.s?.sttUi?.selectedSystemSourceId ?? "";
  }

  async ngOnInit() {
    await this.refreshMics();
    await this.refreshSystemSources();
  }

  async refreshMics() {
    // Pide permiso para que aparezcan labels de micrófonos
    const tmp = await navigator.mediaDevices.getUserMedia({ audio: true });
    tmp.getTracks().forEach((t) => t.stop());

    const devices = await navigator.mediaDevices.enumerateDevices();
    this.micDevices.set(
      devices
        .filter((d) => d.kind === "audioinput")
        .map((d) => ({ deviceId: d.deviceId, label: d.label || "Micrófono (sin nombre)" }))
    );
  }

  async refreshSystemSources() {
    if (!window.prompter?.listSystemAudioSources) {
      this.systemSources.set([]);
      return;
    }
    const sources = await window.prompter.listSystemAudioSources();
    this.systemSources.set(sources);
  }

  onMicChange(deviceId: string) {
    this.settings.updateDeep((st) => {
      st.sttUi.selectedMicId = deviceId || null;
    });
  }

  onSystemSourceChange(sourceId: string) {
    this.settings.updateDeep((st) => {
      st.sttUi.selectedSystemSourceId = sourceId || null;
    });
  }
}
