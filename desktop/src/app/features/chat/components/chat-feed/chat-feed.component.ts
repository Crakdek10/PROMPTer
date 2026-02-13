import { Component, inject, ElementRef, ViewChild, AfterViewChecked } from '@angular/core';
import { ChatStore } from '../../../../core/stores/chat.store';
import { SessionStore } from '../../../../core/stores/session.store';
import { ChatMessageBubbleComponent } from '../chat-message-bubble/chat-message-bubble.component';
import {ChatPlaceholderComponent} from '../chat-placeholder/chat-placeholder.component';

@Component({
  selector: 'app-chat-feed',
  standalone: true,
  imports: [ChatMessageBubbleComponent, ChatPlaceholderComponent],
  templateUrl: './chat-feed.component.html',
  styles: [`
    .scrollbar-thin::-webkit-scrollbar { width: 6px; }
    .scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
    .scrollbar-thin::-webkit-scrollbar-thumb { background-color: rgba(255, 255, 255, 0.1); border-radius: 20px; }
    .scrollbar-thin::-webkit-scrollbar-thumb:hover { background-color: rgba(255, 255, 255, 0.2); }
  `]
})
export class ChatFeedComponent implements AfterViewChecked {
  readonly chatStore = inject(ChatStore);
  readonly sessionStore = inject(SessionStore);

  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    try {
      this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
    } catch(err) { }
  }
}
