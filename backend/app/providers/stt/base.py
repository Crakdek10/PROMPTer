from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class STTAudioFrame:
    session_id: str
    audio_bytes: bytes
    format: str
    sample_rate: int
    chunk_index: int

class STTProvider(ABC):
    name: str

    @abstractmethod
    async def on_start(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def on_audio(self, frame: STTAudioFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def on_stop(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        ...