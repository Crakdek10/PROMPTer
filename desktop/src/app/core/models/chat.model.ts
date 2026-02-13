export type ChatAuthor = "user" | "ai" | "system";
export type TranscriptKind = "partial" | "final";

export interface TranscriptChunk {
  kind: TranscriptKind;
  text: string;
  session_id?: string | null;
  is_final?: boolean;
  start_ms?: number | null;
  end_ms?: number | null;
}

export interface ChatMessage {
  id: string;
  author: ChatAuthor;
  text: string;
  createdAt: number;
  sessionId?: string | null;
  favorite?: boolean;
  status?: "final" | "streaming" | "error";
  transcriptKind?: TranscriptKind;
}
