from __future__ import annotations
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Any, Optional
import json
from app.utils.ws_protocol import b64_to_bytes

router = APIRouter(tags=["stt"])

@router.websocket("/ws/stt")
async def ws_stt(websocket: WebSocket) -> None:
    await websocket.accept()

    session_id: Optional[str] = None
    audio_chunks = 0

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

            msg_type = msg.get("type")

            if msg_type == "start":
                session_id = msg.get("session_id")
                if not session_id:
                    await send({"type": "error", "message": "Missing session_id"})
                    continue

                audio_chunks = 0
                await send({"type": "ready", "session_id": session_id})

            elif msg_type == "audio":
                if not session_id:
                    await send({"type": "error", "message": "Send 'start' first"})
                    continue

                fmt = msg.get("format")
                sr = msg.get("sample_rate")
                data = msg.get("data")

                if fmt != "pcm16":
                    await send({"type": "error", "message": "Only format=pcm16 supported", "session_id": session_id})
                    continue
                if not isinstance(sr, int) or sr <= 0:
                    await send({"type": "error", "message": "Invalid sample_rate", "session_id": session_id})
                    continue
                if not isinstance(data, str) or not data:
                    await send({"type": "error", "message": "Missing audio data", "session_id": session_id})
                    continue

                try:
                    _audio_bytes = b64_to_bytes(data)
                except ValueError as e:
                    await send({"type": "error", "message": str(e), "session_id": session_id})
                    continue

                audio_chunks += 1

                await send({"type": "partial", "session_id": session_id, "text": f"(mock) escuchando... chunk={audio_chunks}"})

                if audio_chunks % 3 == 0:
                    await send({"type": "final", "session_id": session_id, "text": f"(mock) transcripción final #{audio_chunks//3}"})

            elif msg_type == "stop":
                if session_id:
                    await send({"type": "final", "session_id": session_id, "text": "(mock) stop"})
                await websocket.close()
                return

            else:
                await send({"type": "error", "message": "Unknown message type", "session_id": session_id or ""})

    except WebSocketDisconnect:
        return
