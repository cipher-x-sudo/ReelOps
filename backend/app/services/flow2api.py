from __future__ import annotations

from typing import Any

import httpx

from ..config import settings


class Flow2ApiClient:
    async def submit_generation(self, *, model: str, prompt: str, stream: bool = False) -> dict[str, Any]:
        if not settings.flow2api_api_key:
            return {
                "mode": "dry_run",
                "model": model,
                "prompt": prompt,
                "message": "FLOW2API_API_KEY is not configured; no upstream generation was submitted.",
            }
        url = f"{settings.flow2api_base_url.rstrip('/')}/v1/async/chat/completions"
        headers = {"Authorization": f"Bearer {settings.flow2api_api_key}", "Content-Type": "application/json"}
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": stream}
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()

