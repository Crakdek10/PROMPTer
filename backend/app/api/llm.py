from __future__ import annotations
from typing import Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.llm_router import LLMRouter
from app.providers.llm.base import LLMGenerateRequest, LLMMessage
from app.core.errors import ProviderError, ConfigError

router = APIRouter(prefix="/llm", tags=["llm"])

_llm_router = LLMRouter()

class MessageIn(BaseModel):
    role: str
    content: str

class LLMGenerateIn(BaseModel):
    messages: list[MessageIn]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=256, ge=1, le=8192)
    provider: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] | None = None

class LLMGenerateOut(BaseModel):
    text: str
    provider: str
    model: Optional[str] = None
    usage: dict[str, Any] | None = None

@router.post("/generate", response_model=LLMGenerateOut)
async def generate_llm(payload: LLMGenerateIn) -> LLMGenerateOut:
    req = LLMGenerateRequest(
        messages=[LLMMessage(role=m.role, content=m.content) for m in payload.messages],
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        provider=payload.provider,
        extra=payload.extra,
    )

    try:
        res = await _llm_router.generate(req, payload.config)
        return LLMGenerateOut(text=res.text, provider=res.provider, model=res.model, usage=res.usage)

    except NotImplementedError:
        raise ProviderError("Provider not implemented yet", provider=payload.provider or "")

    except ValueError as e:
        raise ConfigError(str(e))

    except Exception as e:
        raise ProviderError(str(e), provider=payload.provider or "")
