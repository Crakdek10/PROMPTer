from __future__ import annotations
import os
import tempfile
import subprocess
from typing import Any, Optional
from app.core.config import get_settings
from app.providers.stt.base import STTAudioFrame, STTProvider
from app.services.session_store import SessionStore
from app.utils.wav import pcm16_to_wav_bytes


class WhisperSelfHostedSTTProvider(STTProvider):
    name = "whisper_selfhosted"

    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self.settings = get_settings()

    def _pick_bin(self, config: dict[str, Any]) -> str:
        b = config.get("whisper_bin")
        if isinstance(b, str) and b.strip():
            return b.strip()
        if self.settings.WHISPER_CPP_BIN:
            return self.settings.WHISPER_CPP_BIN
        raise ValueError("WHISPER_CPP_BIN not configured (env or config.whisper_bin)")

    def _pick_model(self, config: dict[str, Any]) -> str:
        m = config.get("model")
        if isinstance(m, str) and m.strip():
            if "/" not in m:
                return os.path.join("/home/ubuntu/whisper.cpp/models", m.strip())
            return m.strip()

        if self.settings.WHISPER_CPP_MODEL:
            return self.settings.WHISPER_CPP_MODEL

        raise ValueError("WHISPER_CPP_MODEL not configured (env or config.model)")

    def _pick_lang(self, config: dict[str, Any]) -> Optional[str]:
        lang = config.get("lang")
        if isinstance(lang, str) and lang.strip():
            return lang.strip()
        if self.settings.WHISPER_CPP_LANG and self.settings.WHISPER_CPP_LANG.strip():
            return self.settings.WHISPER_CPP_LANG.strip()
        return None

    async def on_start(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        _ = self._pick_bin(config)
        _ = self._pick_model(config)

        sess = self.store.get(session_id)
        if sess:
            sess.audio_bytes.clear()
            sess.audio_chunks = 0

        return [{"type": "ready", "session_id": session_id}]

    async def on_audio(self, frame: STTAudioFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
        self.store.append_audio(frame.session_id, frame.audio_bytes)

        return [{
            "type": "partial",
            "session_id": frame.session_id,
            "text": f"(whisper.cpp) recibiendo audio… chunk={frame.chunk_index}",
        }]

    async def on_stop(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        pcm = self.store.pop_audio(session_id)
        if not pcm:
            return [{"type": "final", "session_id": session_id, "text": ""}]

        sample_rate = int(config.get("sample_rate") or 16000)

        wav_bytes = pcm16_to_wav_bytes(pcm, sample_rate=sample_rate, channels=1)

        whisper_bin = self._pick_bin(config)
        whisper_model = self._pick_model(config)
        lang = self._pick_lang(config)

        with tempfile.TemporaryDirectory(prefix="prompter_whisper_") as td:
            wav_path = os.path.join(td, "audio.wav")
            out_path = os.path.join(td, "out.txt")

            with open(wav_path, "wb") as f:
                f.write(wav_bytes)

            out_prefix = os.path.join(td, "out")

            cmd = [
                whisper_bin,
                "-m", whisper_model,
                "-f", wav_path,
                "-otxt",
                "-of", out_prefix,
            ]
            if lang:
                cmd.extend(["-l", lang])

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()
                raise ValueError(f"whisper.cpp failed: {err[:500]}")

            txt_file = out_prefix + ".txt"
            text = ""
            try:
                with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().strip()
            except FileNotFoundError:
                text = (proc.stdout or "").strip()

        return [{"type": "final", "session_id": session_id, "text": text}]
