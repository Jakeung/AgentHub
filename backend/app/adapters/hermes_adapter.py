"""Adapter for Hermes Agent HTTP API (OpenAI-compatible)."""
import json
import logging
from typing import AsyncIterator
import httpx

logger = logging.getLogger(__name__)


class HermesAdapter:
    """Proxy to Hermes Agent container's /v1/chat/completions endpoint."""

    def __init__(self, port: int, timeout: float = 120.0, api_key: str = "", container_name: str = ""):
        if container_name:
            self.base_url = f"http://{container_name}:8642"
        else:
            self.base_url = f"http://localhost:{port}"
        self.timeout = timeout
        self.api_key = api_key
        self.last_usage: dict | None = None

    async def chat_stream(
        self,
        messages: list[dict],
        model: str = "hermes",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream chat completions from Hermes Agent via SSE."""
        self.last_usage = None
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(f"Hermes API error {response.status_code}: {body.decode()}")

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data)
                        usage = chunk.get("usage")
                        if usage:
                            self.last_usage = usage
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> bool:
        """Check if the Hermes Agent is responsive."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
