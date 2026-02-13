import { Component, EventEmitter, Input, Output, inject } from "@angular/core";
import { SessionStore } from "../../../../core/stores/session.store";

@Component({
  selector: "app-bottom-controls",
  standalone: true,
  templateUrl: "./bottom-controls.component.html",
})
export class BottomControlsComponent {
  private readonly session = inject(SessionStore);

  @Input() isRunning = false;
  @Output() stop = new EventEmitter<void>();

  async toggleRec() {
    if (this.isRunning) {
      await this.session.stopSession();
    } else {
      await this.session.startSession();
    }
  }
}
