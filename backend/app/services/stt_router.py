from __future__ import annotations
from typing import Any, Optional

from app.services.session_store import SessionStore
from app.utils.ws_protocol import b64_to_bytes
from app.utils.validate import (
    DEFAULT_AUDIO_CONSTRAINTS,
    validate_audio_bytes_size,
    validate_b64_string,
    validate_format,
    validate_sample_rate,
)
from app.providers.stt.base import STTAudioFrame, STTProvider
from app.providers.stt.cloud_stub import CloudStubSTTProvider
from app.providers.stt.custom_ws_proxy import CustomWSProxySTTProvider
from app.providers.stt.whisper_selfhosted import WhisperSelfHostedSTTProvider
from app.providers.stt.whisper_cpp import WhisperCppSTTProvider


class STTRouter:
    def __init__(self, store: SessionStore) -> None:
        self.store = store

        self._providers: dict[str, STTProvider] = {
            CloudStubSTTProvider.name: CloudStubSTTProvider(),
            CustomWSProxySTTProvider.name: CustomWSProxySTTProvider(),
            WhisperSelfHostedSTTProvider.name: WhisperSelfHostedSTTProvider(self.store),
            WhisperCppSTTProvider.name: WhisperCppSTTProvider(self.store),
        }


        self._audio_constraints = DEFAULT_AUDIO_CONSTRAINTS

    def _pick_provider(self, config: dict[str, Any]) -> STTProvider:
        name = config.get("provider", "cloud_stub")
        if not isinstance(name, str) or not name:
            name = "cloud_stub"
        provider = self._providers.get(name)
        if not provider:
            raise ValueError(f"Unknown STT provider: {name}")
        return provider

    async def handle(
        self,
        msg: dict[str, Any],
        current_session_id: Optional[str],
    ) -> tuple[Optional[str], list[dict[str, Any]], bool]:
        msg_type = msg.get("type")

        if msg_type == "start":
            return await self._handle_start(msg)

        if msg_type == "audio":
            return await self._handle_audio(msg, current_session_id)

        if msg_type == "stop":
            return await self._handle_stop(current_session_id)

        sid = current_session_id or ""
        return sid, [{"type": "error", "message": "Unknown message type", "session_id": sid}], False

    async def _handle_start(self, msg: dict[str, Any]) -> tuple[Optional[str], list[dict[str, Any]], bool]:
        session_id = msg.get("session_id")
        if not session_id:
            return None, [{"type": "error", "message": "Missing session_id"}], False

        config = msg.get("config")
        if config is None:
            config = {}
        if not isinstance(config, dict):
            return None, [{"type": "error", "message": "Invalid config (must be object)"}], False

        self.store.create(session_id=session_id, config=config)

        try:
            provider = self._pick_provider(config)
            out = await provider.on_start(session_id, config)
            return session_id, out, False
        except Exception as e:
            self.store.close(session_id)
            return None, [{"type": "error", "message": str(e), "session_id": session_id}], False

    async def _handle_audio(
        self,
        msg: dict[str, Any],
        current_session_id: Optional[str],
    ) -> tuple[Optional[str], list[dict[str, Any]], bool]:
        if not current_session_id:
            return None, [{"type": "error", "message": "Send 'start' first"}], False

        sess = self.store.get(current_session_id)
        if not sess:
            return None, [{"type": "error", "message": "Send 'start' first"}], False

        try:
            fmt = validate_format(msg.get("format"), self._audio_constraints)
            sr = validate_sample_rate(msg.get("sample_rate"), self._audio_constraints)
            data = validate_b64_string(msg.get("data"))
        except ValueError as e:
            return current_session_id, [{"type": "error", "message": str(e), "session_id": current_session_id}], False

        try:
            audio_bytes = b64_to_bytes(data)
        except ValueError as e:
            return current_session_id, [{"type": "error", "message": str(e), "session_id": current_session_id}], False

        try:
            validate_audio_bytes_size(audio_bytes, self._audio_constraints)
        except ValueError as e:
            return current_session_id, [{"type": "error", "message": str(e), "session_id": current_session_id}], False

        try:
            chunk_index = self.store.inc_audio_count(current_session_id)
        except ValueError as e:
            return current_session_id, [{"type": "error", "message": str(e), "session_id": current_session_id}], False

        try:
            provider = self._pick_provider(sess.config)
            frame = STTAudioFrame(
                session_id=current_session_id,
                audio_bytes=audio_bytes,
                format=fmt,
                sample_rate=sr,
                chunk_index=chunk_index,
            )
            out = await provider.on_audio(frame, sess.config)
            return current_session_id, out, False
        except NotImplementedError:
            return current_session_id, [{"type": "error", "message": "Provider not implemented yet", "session_id": current_session_id}], False
        except Exception as e:
            return current_session_id, [{"type": "error", "message": str(e), "session_id": current_session_id}], False

    async def _handle_stop(self, current_session_id: Optional[str]) -> tuple[Optional[str], list[dict[str, Any]], bool]:
        if current_session_id:
            sess = self.store.get(current_session_id)
            config = sess.config if sess else {}

            try:
                provider = self._pick_provider(config)
                out = await provider.on_stop(current_session_id, config)
            except NotImplementedError:
                out = [{"type": "final", "session_id": current_session_id, "text": "(mock) stop"}]
            except Exception as e:
                out = [{"type": "error", "message": str(e), "session_id": current_session_id}]

            self.store.close(current_session_id)
            return current_session_id, out, True

        return None, [], True
