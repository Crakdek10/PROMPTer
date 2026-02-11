from __future__ import annotations
from fastapi import APIRouter
from app.providers.stt.cloud_stub import CloudStubSTTProvider
from app.providers.stt.custom_ws_proxy import CustomWSProxySTTProvider
from app.providers.stt.whisper_selfhosted import WhisperSelfHostedSTTProvider
from app.providers.llm.openai_compat import OpenAICompatLLMProvider
from app.providers.llm.gemini import GeminiLLMProvider

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/stt")
def list_stt_providers() -> dict:
    items = [
        {
            "name": CloudStubSTTProvider.name,
            "type": "stt",
            "status": "ready",
            "description": "Mock realista (partial por chunk, final cada 3).",
        },
        {
            "name": CustomWSProxySTTProvider.name,
            "type": "stt",
            "status": "skeleton",
            "description": "Proxy WS a STT externo (pendiente implementar).",
        },
        {
            "name": WhisperSelfHostedSTTProvider.name,
            "type": "stt",
            "status": "skeleton",
            "description": "Whisper self-hosted (pendiente implementar).",
        },
    ]
    return {"items": items}


@router.get("/llm")
def list_llm_providers() -> dict:
    items = [
        {
            "name": OpenAICompatLLMProvider.name,
            "type": "llm",
            "status": "ready",
            "description": "API OpenAI-compatible (chat/completions).",
        },
        {
            "name": GeminiLLMProvider.name,
            "type": "llm",
            "status": "skeleton",
            "description": "Gemini (pendiente implementar).",
        },
    ]
    return {"items": items}