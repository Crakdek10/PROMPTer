from __future__ import annotations
from typing import Any
from app.providers.llm.base import LLMGenerateRequest, LLMGenerateResponse, LLMProvider
from app.providers.llm.openai_compat import OpenAICompatLLMProvider
from app.providers.llm.gemini import GeminiLLMProvider

class LLMRouter:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {
            OpenAICompatLLMProvider.name: OpenAICompatLLMProvider(),
            GeminiLLMProvider.name: GeminiLLMProvider(),
        }

    def list_providers(self) -> list[str]:
        return sorted(self._providers.keys())

    def _pick_provider(self, config: dict[str, Any], req_provider: str | None) -> LLMProvider:
        name = req_provider or config.get("provider") or "openai_compat"
        if not isinstance(name, str) or not name:
            name = "openai_compat"
        provider = self._providers.get(name)
        if not provider:
            raise ValueError(f"Unknown LLM provider: {name}")
        return provider

    async def generate(self, req: LLMGenerateRequest, config: dict[str, Any]) -> LLMGenerateResponse:
        provider = self._pick_provider(config, req.provider)
        return await provider.generate(req, config)
