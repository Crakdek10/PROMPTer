import { Component, Input, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { ChatMessage } from "../../../../core/models/chat.model";
import { ChatStore } from "../../../../core/stores/chat.store";

@Component({
  selector: "app-chat-message-bubble",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./chat-message-bubble.component.html",
})
export class ChatMessageBubbleComponent {
  private readonly chat = inject(ChatStore);

  @Input({ required: true }) message!: ChatMessage;
  @Input() isAi: boolean = false;

  get author() {
    return this.message.author;
  }

  async onCopy() {
    await this.chat.copy(this.message.id);
  }

  onStar() {
    this.chat.toggleFavorite(this.message.id);
  }

  onTranslate() {
    this.chat.translate(this.message.id);
  }

  onGenerate() {
    this.chat.generateFromSystem(this.message.id);
  }

  onForward() {
    this.chat.forwardToTeleprompter(this.message.id);
  }
}
