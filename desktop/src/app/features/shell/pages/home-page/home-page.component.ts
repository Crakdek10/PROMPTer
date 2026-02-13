import {Component, inject, signal} from '@angular/core';
import { ChatPageComponent } from '../../../chat/pages/chat-page/chat-page.component';
import { SessionStore } from '../../../../core/stores/session.store';
import { BottomControlsComponent } from '../../../controls/components/bottom-controls/bottom-controls.component';
import { SettingsDrawerComponent } from '../../../settings/components/settings-drawer/settings-drawer.component';

@Component({
  selector: 'app-home-page',
  standalone: true,
  imports: [ChatPageComponent, SettingsDrawerComponent, BottomControlsComponent],
  templateUrl: './home-page.component.html',
})
export class HomePageComponent {
  readonly collapsed = signal(false);
  readonly hoveringDrawer = signal(false);
  readonly isClosing = signal(false);
  readonly previewT = signal(0);
  readonly sessionStore = inject(SessionStore);

  // tamaños
  readonly drawerW = 320;   // ancho abierto real
  readonly peek = 40;       // strip colapsado visible
  readonly hoverPeek = 65;  // preview en hover
  readonly gap = 16;        // gap-4
  readonly outerPad = 16;   // p-4

  toggle() {
    const willCollapse = !this.collapsed();

    if (willCollapse) {
      this.isClosing.set(true);
      this.hoveringDrawer.set(false);
      this.previewT.set(0);
      setTimeout(() => this.isClosing.set(false), 160);
    }

    this.collapsed.update(v => !v);

    if (!willCollapse) {
      this.previewT.set(0);
      this.hoveringDrawer.set(false);
    }
  }

  get isPreview(): boolean {
    return this.collapsed() && this.hoveringDrawer();
  }

  get visibleDrawerWidth(): number {
    if (!this.collapsed()) return this.drawerW;
    return this.peek + (this.hoverPeek - this.peek) * this.previewT();
  }

  /** 🔥 Drawer pegado a la pared SOLO cuando está colapsado */
  get drawerRightOffset(): number {
    return this.collapsed() ? -this.outerPad : 0;
  }

  /** 🔥 Espacio que realmente “invade” dentro del área con padding */
  private get drawerInLayout(): number {
    if (!this.collapsed()) return this.visibleDrawerWidth;
    return Math.max(0, this.visibleDrawerWidth - this.outerPad);
  }

  /** empuje del chat */
  get chatRightPad(): number {
    return this.drawerInLayout + this.gap;
  }

  get previewOpacity(): number {
    if (!this.collapsed()) return 1;
    const min = 0.10;
    const max = 0.40;
    const t = this.previewT();
    return min + (max - min) * t;
  }

  onDrawerEnter() {
    if (!this.collapsed()) return;
    if (this.isClosing()) return;
    this.hoveringDrawer.set(true);
    this.animatePreviewTo(1);
  }

  onDrawerLeave() {
    if (this.isClosing()) return;
    this.animatePreviewTo(0);
    setTimeout(() => this.hoveringDrawer.set(false), 280);
  }

  private animatePreviewTo(target: 0 | 1) {
    const start = this.previewT();
    const startTime = performance.now();
    const duration = 280;

    const step = (now: number) => {
      const p = Math.min(1, (now - startTime) / duration);
      const eased = p * p * (3 - 2 * p);
      this.previewT.set(start + (target - start) * eased);
      if (p < 1) requestAnimationFrame(step);
    };

    requestAnimationFrame(step);
  }
}
