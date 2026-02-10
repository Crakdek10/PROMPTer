from __future__ import annotations
from typing import Any, Literal, TypedDict, NotRequired, Optional, List
import base64

ClientMsgType = Literal["start", "audio", "stop"]
ServerMsgType = Literal["ready", "partial", "final", "error"]

AudioFormat = Literal["pcm16"]

class ClientStart(TypedDict):
    type: Literal["start"]
    session_id: str
    config: NotRequired[dict[str, Any]]

class ClientAudio(TypedDict):
    type: Literal["audio"]
    format: AudioFormat
    sample_rate: int
    data: str

class ClientStop(TypedDict):
    type: Literal["stop"]

ClientMessage = ClientStart | ClientAudio | ClientStop

class ServerReady(TypedDict):
    type: Literal["ready"]
    session_id: str

class ServerPartial(TypedDict):
    type: Literal["partial"]
    session_id: str
    text: str

class ServerFinal(TypedDict):
    type: Literal["final"]
    session_id: str
    text: str

class ServerError(TypedDict):
    type: Literal["error"]
    message: str
    session_id: NotRequired[str]

ServerMessage = ServerReady | ServerPartial | ServerFinal | ServerError

def b64_to_bytes(data_b64: str) -> bytes:
    try:
        return base64.b64decode(data_b64)
    except Exception as e:
        raise ValueError("Invalid base64 audio payload") from e