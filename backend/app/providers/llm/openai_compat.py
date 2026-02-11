from __future__ import annotations
from typing import Any, Optional
import httpx
from app.providers.llm.base import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    LLMProvider,
)

class OpenAICompatLLMProvider(LLMProvider):
    name = "openai_compat"

    def _validate(self, config: dict[str, Any]) -> tuple[str, str, str, float]:
        base_url = config.get("base_url")
        api_key = config.get("api_key")
        model = config.get("model")
        timeout_s = config.get("timeout_s", 30)

        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            raise ValueError("openai_compat requires config.base_url as http(s) URL")
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("openai_compat requires config.api_key")
        if not isinstance(model, str) or not model:
            raise ValueError("openai_compat requires config.model")
        if not isinstance(timeout_s, (int, float)) or timeout_s <= 0:
            raise ValueError("openai_compat config.timeout_s must be > 0")

        return base_url.rstrip("/"), api_key, model, float(timeout_s)

    async def generate(self, req: LLMGenerateRequest, config: dict[str, Any]) -> LLMGenerateResponse:
        base_url, api_key, model, timeout_s = self._validate(config)

        url = f"{base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }

        if req.extra:
            payload.update(req.extra)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        text: Optional[str] = None
        try:
            text = data["choices"][0]["message"]["content"]
        except Exception:
            text = None

        if not text:
            raise ValueError("openai_compat: invalid response format (missing choices[0].message.content)")

        usage = data.get("usage")
        return LLMGenerateResponse(text=text, provider=self.name, model=model, usage=usage)