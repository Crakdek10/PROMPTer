from __future__ import annotations
import asyncio
import json
import time
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.session_store import SessionStore
from app.services.stt_router import STTRouter
from app.providers.stt.whisper_selfhosted import WhisperSelfHostedSTTProvider

router = APIRouter(tags=["stt"])

_store = SessionStore()
_stt_router = STTRouter(_store)

@router.websocket("/ws/stt")
async def ws_stt(websocket: WebSocket) -> None:
    await websocket.accept()

    session_id: Optional[str] = None
    partial_task: Optional[asyncio.Task] = None

    async def send(msg: dict[str, Any]) -> None:
        await websocket.send_text(json.dumps(msg, ensure_ascii=False))

    async def partial_loop(sid: str) -> None:
        sess = _store.get(sid)
        if not sess:
            return

        config = sess.config or {}
        provider = _stt_router._pick_provider(config)  # usamos el mismo provider elegido

        # Solo soportamos parciales reales si el provider expone transcribe_pcm
        # (en nuestro caso whisper_selfhosted)
        if not hasattr(provider, "transcribe_pcm"):
            return

        every_s = float(config.get("partial_every_s") or 1.6)      # frecuencia
        window_s = float(config.get("partial_window_s") or 6.0)    # últimos N segundos
        min_window_s = float(config.get("partial_min_window_s") or 2.0)

        last_text = ""
        while True:
            await asyncio.sleep(every_s)

            sess2 = _store.get(sid)
            if not sess2:
                return

            sr = int((sess2.config or {}).get("sample_rate") or 16000)

            snap = _store.snapshot_last_seconds(sid, window_s, sr, channels=1)
            if not snap:
                continue

            # evita transcribir si aún hay poquísimo audio
            seconds = len(snap) / (sr * 2)
            if seconds < min_window_s:
                continue

            try:
                text = await provider.transcribe_pcm(snap, sess2.config)
                text = (text or "").strip()
            except Exception:
                text = ""

            # manda partial solo si cambió y no está vacío
            if text and text != last_text:
                last_text = text
                await send({"type": "partial", "session_id": sid, "text": text})

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send({"type": "error", "message": "Invalid JSON"})
                continue

            if not isinstance(msg, dict):
                await send({"type": "error", "message": "Invalid message (must be object)"})
                continue

            msg_type = msg.get("type")

            # START: crea sesión + arranca task de parciales
            if msg_type == "start":
                new_session_id, out_messages, should_close = await _stt_router.handle(msg, session_id)
                session_id = new_session_id if new_session_id else session_id

                for out in out_messages:
                    await send(out)

                # arrancar partial loop solo cuando ya hay session_id válida
                if session_id and partial_task is None:
                    partial_task = asyncio.create_task(partial_loop(session_id))

                if should_close:
                    await websocket.close()
                    return
                continue

            # AUDIO: pasa al router (que solo acumula)
            if msg_type == "audio":
                new_session_id, out_messages, should_close = await _stt_router.handle(msg, session_id)
                session_id = new_session_id if new_session_id else session_id
                for out in out_messages:
                    await send(out)
                if should_close:
                    await websocket.close()
                    return
                continue

            # STOP: cancela parciales + final + cierra
            if msg_type == "stop":
                if partial_task:
                    partial_task.cancel()
                    try:
                        await partial_task
                    except Exception:
                        pass
                    partial_task = None

                new_session_id, out_messages, should_close = await _stt_router.handle(msg, session_id)
                session_id = new_session_id if new_session_id else session_id

                for out in out_messages:
                    await send(out)

                if should_close:
                    await websocket.close()
                return

            await send({"type": "error", "message": "Unknown message type", "session_id": session_id or ""})

    except WebSocketDisconnect:
        if partial_task:
            partial_task.cancel()
        if session_id:
            _store.close(session_id)
        return
