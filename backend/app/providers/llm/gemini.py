from __future__ import annotations
from typing import Any
from app.providers.llm.base import LLMGenerateRequest, LLMGenerateResponse, LLMProvider

class GeminiLLMProvider(LLMProvider):
    name = "gemini"

    def _validate(self, config: dict[str, Any]) -> None:
        api_key = config.get("api_key")
        model = config.get("model")
        if api_key is not None and not isinstance(api_key, str):
            raise ValueError("gemini config.api_key must be string if provided")
        if model is not None and not isinstance(model, str):
            raise ValueError("gemini config.model must be string if provided")

    async def generate(self, req: LLMGenerateRequest, config: dict[str, Any]) -> LLMGenerateResponse:
        self._validate(config)
        raise NotImplementedError("gemini provider not implemented yet")