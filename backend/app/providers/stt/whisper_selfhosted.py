from __future__ import annotations

from typing import Any

from app.providers.stt.base import STTAudioFrame, STTProvider


class WhisperSelfHostedSTTProvider(STTProvider):
    name = "whisper_selfhosted"

    def _validate(self, config: dict[str, Any]) -> None:
        base_url = config.get("base_url")
        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            raise ValueError("whisper_selfhosted requires config.base_url as http(s) URL")

        model = config.get("model")
        if model is not None and not isinstance(model, str):
            raise ValueError("whisper_selfhosted config.model must be string if provided")

    async def on_start(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        self._validate(config)
        raise NotImplementedError("whisper_selfhosted not implemented yet")

    async def on_audio(self, frame: STTAudioFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
        self._validate(config)
        raise NotImplementedError("whisper_selfhosted not implemented yet")

    async def on_stop(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        self._validate(config)
        raise NotImplementedError("whisper_selfhosted not implemented yet")