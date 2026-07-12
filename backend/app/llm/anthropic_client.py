"""Thin wrapper around the Anthropic SDK.

All agents call Claude through this module so the provider can be swapped or
mocked in tests. A local-model fallback can be slotted in here later.
"""

import json
from functools import lru_cache
from typing import Any, Protocol

import anthropic

from app.config import get_settings


class LLMClient(Protocol):
    def complete(self, *, model: str, system: str, prompt: str, max_tokens: int = 16000) -> str: ...

    def complete_json(
        self, *, model: str, system: str, prompt: str, schema: dict, max_tokens: int = 16000
    ) -> dict: ...


class AnthropicClient:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)

    def complete(self, *, model: str, system: str, prompt: str, max_tokens: int = 16000) -> str:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Model refused the request")
        return "".join(b.text for b in response.content if b.type == "text")

    def complete_json(
        self, *, model: str, system: str, prompt: str, schema: dict, max_tokens: int = 16000
    ) -> dict[str, Any]:
        """Structured output constrained by a JSON schema (output_config.format)."""
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Model refused the request")
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)


@lru_cache
def get_llm() -> AnthropicClient:
    return AnthropicClient()
