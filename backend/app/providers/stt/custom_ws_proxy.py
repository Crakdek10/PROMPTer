from __future__ import annotations
from typing import Any
from app.providers.stt.base import STTAudioFrame, STTProvider

class CustomWSProxySTTProvider(STTProvider):
    name = "custom_ws_proxy"

    def _validate(self, config: dict[str, Any]) -> None:
        endpoint = config.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint.startswith(("ws://", "wss://")):
            raise ValueError("custom_ws_proxy requires config.endpoint as ws:// or wss:// URL")

    async def on_start(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        self._validate(config)
        raise NotImplementedError("custom_ws_proxy not implemented yet")

    async def on_audio(self, frame: STTAudioFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
        self._validate(config)
        raise NotImplementedError("custom_ws_proxy not implemented yet")

    async def on_stop(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        self._validate(config)
        raise NotImplementedError("custom_ws_proxy not implemented yet")