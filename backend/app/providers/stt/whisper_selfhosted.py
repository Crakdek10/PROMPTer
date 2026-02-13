from __future__ import annotations
import os
import shutil
import tempfile
import subprocess
import asyncio
import time
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

    def _normalize_bin_path(self, p: str) -> str:
        p = p.strip()

        # Si te pasan un nombre (no ruta), intenta resolver por PATH
        if "/" not in p and "\\" not in p:
            resolved = shutil.which(p)
            if resolved:
                return resolved
            return p

        # Si te pasaron .../main (viejo), intenta cambiar a whisper-cli (nuevo)
        base = os.path.basename(p)
        if base == "main":
            candidate = os.path.join(os.path.dirname(p), "whisper-cli")
            if os.path.exists(candidate):
                return candidate

        # Si te pasaron una ruta, úsala tal cual
        return p

    def _pick_bin(self, config: dict[str, Any]) -> str:
        # 1) config override
        b = config.get("whisper_bin")
        if isinstance(b, str) and b.strip():
            path = self._normalize_bin_path(b)
            if os.path.exists(path) or shutil.which(path):
                return path
            raise ValueError(f"WHISPER_CPP_BIN not found: {path}")

        # 2) env
        env_bin = self.settings.WHISPER_CPP_BIN
        if isinstance(env_bin, str) and env_bin.strip():
            path = self._normalize_bin_path(env_bin)
            if os.path.exists(path) or shutil.which(path):
                return path
            raise ValueError(f"WHISPER_CPP_BIN not found: {path}")

        # 3) fallback: buscar whisper-cli en PATH
        which_cli = shutil.which("whisper-cli")
        if which_cli:
            return which_cli

        # 4) fallback: buscar main en PATH (viejo)
        which_main = shutil.which("main")
        if which_main:
            return which_main

        raise ValueError("WHISPER_CPP_BIN not configured or not found (set env WHISPER_CPP_BIN)")

    def _pick_model(self, config: dict[str, Any]) -> str:
        m = config.get("model")
        if isinstance(m, str) and m.strip():
            if "/" not in m and "\\" not in m:
                return os.path.join("/home/ubuntu/whisper.cpp/models", m.strip())
            return m.strip()

        if self.settings.WHISPER_CPP_MODEL:
            return self.settings.WHISPER_CPP_MODEL

        raise ValueError("WHISPER_CPP_MODEL not configured (env or config.model)")

    def _pick_lang(self, config: dict[str, Any]) -> Optional[str]:
        # acepta "lang" o "language" desde desktop
        lang = config.get("lang") or config.get("language")
        if isinstance(lang, str) and lang.strip():
            return lang.strip()

        if self.settings.WHISPER_CPP_LANG and self.settings.WHISPER_CPP_LANG.strip():
            return self.settings.WHISPER_CPP_LANG.strip()

        return None

    async def _transcribe_pcm_to_text(self, pcm: bytes, config: dict[str, Any]) -> str:
        sample_rate = int(config.get("sample_rate") or 16000)
        wav_bytes = pcm16_to_wav_bytes(pcm, sample_rate=sample_rate, channels=1)
    
        whisper_bin = self._pick_bin(config)
        whisper_model = self._pick_model(config)
        lang = self._pick_lang(config)
    
        # TIP: para parciales usa un modelo más rápido si quieres (base/small)
        with tempfile.TemporaryDirectory(prefix="prompter_whisper_partial_") as td:
            wav_path = os.path.join(td, "audio.wav")
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
                # en parciales, no mates la sesión por fallos puntuales
                return ""
    
            txt_file = out_prefix + ".txt"
            try:
                with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read().strip()
            except FileNotFoundError:
                return (proc.stdout or "").strip()
    

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

        sess = self.store.get(frame.session_id)
        if not sess:
            return []
    
        # Config “rápida” para parciales
        partial_every_s = float(config.get("partial_every_s") or 1.5)
        min_audio_s = float(config.get("partial_min_audio_s") or 1.0)
    
        now = time.monotonic()
    
        # si ya hay un job corriendo, marcamos dirty y salimos
        if sess.partial_running:
            sess.partial_dirty = True
            return []
    
        # throttle
        if sess.last_partial_at and (now - sess.last_partial_at) < partial_every_s:
            return []
    
        # requerir mínimo audio acumulado para que valga la pena
        pcm_snapshot = self.store.snapshot_audio(frame.session_id)
        if not pcm_snapshot:
            return []
    
        sample_rate = int(config.get("sample_rate") or 16000)
        seconds = len(pcm_snapshot) / (sample_rate * 2)  # pcm16 mono
        if seconds < min_audio_s:
            return []
    
        # lanzar partial async (NO bloquea el WS receive loop)
        sess.partial_running = True
        sess.last_partial_at = now
    
        async def run_partial():
            try:
                text = await self._transcribe_pcm_to_text(pcm_snapshot, config)
                text = (text or "").strip()
    
                # evita spam del mismo texto
                if text and text != sess.last_partial_text:
                    sess.last_partial_text = text
                    return [{"type": "partial", "session_id": frame.session_id, "text": text}]
                return []
            finally:
                sess.partial_running = False
    
        out = await run_partial()
    
        # si mientras corría llegaron más chunks, dispara otro parcial “pronto”
        if sess.partial_dirty:
            sess.partial_dirty = False
            # no lo forces inmediato; el próximo on_audio lo tomará
    
        return out

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
            with open(wav_path, "wb") as f:
                f.write(wav_bytes)

            out_prefix = os.path.join(td, "out")

            # ✅ whisper-cli (nuevo) sigue aceptando -m -f -otxt -of
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
