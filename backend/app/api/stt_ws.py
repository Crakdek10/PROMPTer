from __future__ import annotations
import asyncio
import json
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.session_store import SessionStore
from app.services.stt_router import STTRouter

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
        provider = _stt_router._pick_provider(config)

        if not hasattr(provider, "transcribe_pcm"):
            return

        every_s = float(config.get("partial_every_s") or 1.6)
        min_window_s = float(config.get("partial_min_window_s") or 2.0)

        last_text = ""
        while True:
            await asyncio.sleep(every_s)

            sess2 = _store.get(sid)
            if not sess2:
                return  # Termina si la sesión ya no existe

            sr = int((sess2.config or {}).get("sample_rate") or 16000)

            # SOLUCIÓN 1: Tomamos TODO el audio acumulado en lugar de solo los últimos segundos.
            # Esto permite que el texto crezca progresivamente en el frontend.
            snap = _store.snapshot_audio(sid)
            if not snap:
                continue

            seconds = len(snap) / (sr * 2)
            if seconds < min_window_s:
                continue

            try:
                text = await provider.transcribe_pcm(snap, sess2.config)
                text = (text or "").strip()
            except Exception:
                text = ""

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
                await send({"type": "error", "message": "Invalid message"})
                continue

            msg_type = msg.get("type")

            if msg_type == "start":
                new_session_id, out_messages, should_close = await _stt_router.handle(msg, session_id)
                session_id = new_session_id if new_session_id else session_id

                for out in out_messages:
                    await send(out)

                if session_id and partial_task is None:
                    partial_task = asyncio.create_task(partial_loop(session_id))

                if should_close:
                    await websocket.close()
                    return
                continue

            if msg_type == "audio":
                new_session_id, out_messages, should_close = await _stt_router.handle(msg, session_id)
                session_id = new_session_id if new_session_id else session_id
                for out in out_messages:
                    await send(out)
                if should_close:
                    await websocket.close()
                    return
                continue

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