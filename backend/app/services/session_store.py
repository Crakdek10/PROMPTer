from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

@dataclass
class STTSession:
    session_id: str
    config: dict[str, Any]
    audio_chunks: int = 0
    audio_bytes: bytearray = field(default_factory=bytearray)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, STTSession] = {}

    def create(self, session_id: str, config: Optional[dict[str, Any]] = None) -> STTSession:
        if not session_id:
            raise ValueError("Missing session_id")
        sess = STTSession(session_id=session_id, config=config or {})
        self._sessions[session_id] = sess
        return sess

    def get(self, session_id: str) -> Optional[STTSession]:
        return self._sessions.get(session_id)

    def close(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def reset_audio_count(self, session_id: str) -> None:
        sess = self.get(session_id)
        if sess:
            sess.audio_chunks = 0

    def inc_audio_count(self, session_id: str) -> int:
        sess = self.get(session_id)
        if not sess:
            raise ValueError("Send 'start' first")
        sess.audio_chunks += 1
        return sess.audio_chunks

    def append_audio(self, session_id: str, chunk: bytes) -> None:
        sess = self.get(session_id)
        if not sess:
            raise ValueError("Send 'start' first")
        sess.audio_bytes.extend(chunk)

    def pop_audio(self, session_id: str) -> bytes:
        sess = self.get(session_id)
        if not sess:
            return b""
        data = bytes(sess.audio_bytes)
        sess.audio_bytes.clear()
        return data
