from __future__ import annotations

from typing import Any

import httpx

from ..config import settings


class LlmClient:
    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if settings.llm_provider == "openrouter" and settings.openrouter_api_key:
            return await self._chat_json(
                "https://openrouter.ai/api/v1/chat/completions",
                settings.openrouter_api_key,
                settings.llm_model,
                system_prompt,
                user_prompt,
            )
        if settings.llm_provider == "local" and settings.local_llm_base_url:
            return await self._chat_json(
                f"{settings.local_llm_base_url.rstrip('/')}/chat/completions",
                settings.local_llm_api_key,
                settings.llm_model,
                system_prompt,
                user_prompt,
            )
        return {
            "provider": "stub",
            "model": settings.llm_model,
            "title": "Draft reel package",
            "items": [
                "Hook-focused topic generated from the niche guide.",
                "Scene-by-scene prompts are ready for review.",
                "Configure an LLM provider to replace stub output.",
            ],
        }

    async def _chat_json(
        self,
        url: str,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        import json

        return json.loads(content)

