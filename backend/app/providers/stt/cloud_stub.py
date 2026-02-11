from __future__ import annotations
from typing import Any
from app.providers.stt.base import STTAudioFrame, STTProvider

class CloudStubSTTProvider(STTProvider):
    name = "cloud_stub"

    async def on_start(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"type": "ready", "session_id": session_id}]

    async def on_audio(self, frame: STTAudioFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [
            {
                "type": "partial",
                "session_id": frame.session_id,
                "text": f"(mock) escuchando... chunk={frame.chunk_index}",
            }
        ]

        if frame.chunk_index % 3 == 0:
            out.append(
                {
                    "type": "final",
                    "session_id": frame.session_id,
                    "text": f"(mock) transcripción final #{frame.chunk_index // 3}",
                }
            )

        return out

    async def on_stop(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"type": "final", "session_id": session_id, "text": "(mock) stop"}]