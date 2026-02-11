from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str

@dataclass(frozen=True)
class LLMGenerateRequest:
    messages: list[LLMMessage]
    temperature: float = 0.7
    max_tokens: int = 256
    provider: Optional[str] = None
    extra: dict[str, Any] | None = None

@dataclass(frozen=True)
class LLMGenerateResponse:
    text: str
    provider: str
    model: Optional[str] = None
    usage: dict[str, Any] | None = None

class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, req: LLMGenerateRequest, config: dict[str, Any]) -> LLMGenerateResponse:
        ...