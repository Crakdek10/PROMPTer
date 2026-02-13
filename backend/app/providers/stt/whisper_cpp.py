from __future__ import annotations

import asyncio
import os
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional

from app.providers.stt.base import STTAudioFrame, STTProvider
from app.services.session_store import SessionStore


def _pick_int(v: Any, default: int) -> int:
    try:
        n = int(v)
        return n if n > 0 else default
    except Exception:
        return default


def _write_wav_pcm16_mono(path: str, pcm16: bytes, sample_rate: int) -> None:
    # PCM16 mono little-endian
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16)


class WhisperCppSTTProvider(STTProvider):
    """
    MVP:
    - acumula audio pcm16 por sesión (SessionStore)
    - en stop genera wav temporal
    - ejecuta whisper.cpp (main) y devuelve "final"
    """
    name = "whisper_cpp"

    def __init__(self, store: SessionStore) -> None:
        self.store = store

    def _paths(self, config: dict[str, Any]) -> tuple[Path, Path]:
        # config > env > defaults
        base_dir = (config.get("whisper_cpp_dir") or os.getenv("WHISPER_CPP_DIR") or "/home/ubuntu/whisper.cpp").strip()
        bin_path = (config.get("whisper_cpp_bin") or os.getenv("WHISPER_CPP_BIN") or str(Path(base_dir) / "main")).strip()
        model_path = (config.get("whisper_cpp_model") or os.getenv("WHISPER_CPP_MODEL") or str(Path(base_dir) / "models" / "ggml-base.en.bin")).strip()
        return Path(bin_path), Path(model_path)

    async def on_start(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        # nada especial, el store ya creó la sesión
        return [{"type": "ready", "session_id": session_id}]

    async def on_audio(self, frame: STTAudioFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
        if frame.format != "pcm16":
            raise ValueError("whisper_cpp: only pcm16 supported for now")

        # ✅ acumular audio para transcribir en stop
        self.store.append_audio(frame.session_id, frame.audio_bytes)

        # MVP: sin partials por ahora
        return []

    async def on_stop(self, session_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        bin_path, model_path = self._paths(config)

        if not bin_path.exists():
            raise ValueError(f"whisper_cpp: binary not found: {bin_path}")
        if not model_path.exists():
            raise ValueError(f"whisper_cpp: model not found: {model_path}")

        pcm16 = self.store.pop_audio(session_id)
        if not pcm16:
            return [{"type": "final", "session_id": session_id, "text": ""}]

        sample_rate = _pick_int(config.get("sample_rate"), 16000)
        timeout_s = _pick_int(config.get("timeout_s"), 60)

        lang = (config.get("language") or "auto").strip()

        with tempfile.TemporaryDirectory(prefix="prompter_stt_") as td:
            wav_path = str(Path(td) / "audio.wav")
            _write_wav_pcm16_mono(wav_path, pcm16, sample_rate)

            args = [str(bin_path), "-m", str(model_path), "-f", wav_path]

            # language opcional
            if lang and lang != "auto":
                args += ["-l", lang]

            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
            except asyncio.TimeoutError:
                proc.kill()
                raise ValueError(f"whisper_cpp: timeout after {timeout_s}s")

            out = (out_b or b"").decode("utf-8", errors="ignore").strip()
            err = (err_b or b"").decode("utf-8", errors="ignore").strip()

            if proc.returncode != 0:
                raise ValueError(f"whisper_cpp: exit {proc.returncode}: {err[:800]}")

            text = out if out else err
            text = (text or "").strip()

            if not text:
                raise ValueError("whisper_cpp: empty transcription output")

            return [{"type": "final", "session_id": session_id, "text": text}]
