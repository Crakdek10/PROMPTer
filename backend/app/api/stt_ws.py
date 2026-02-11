from __future__ import annotations
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

    async def send(msg: dict[str, Any]) -> None:
        await websocket.send_text(json.dumps(msg, ensure_ascii=False))

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

            try:
                new_session_id, out_messages, should_close = await _stt_router.handle(msg, session_id)
            except Exception as e:
                await send({"type": "error", "message": str(e), "session_id": session_id or ""})
                continue

            session_id = new_session_id if new_session_id is not None else session_id

            for out in out_messages:
                await send(out)

            if should_close:
                await websocket.close()
                return

    except WebSocketDisconnect:
        if session_id:
            _store.close(session_id)
        return