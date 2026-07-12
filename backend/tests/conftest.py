"""Test fixtures. All tests run offline: no database, no API keys."""

from typing import Any

import pytest

from app.agents.state import Services


class FakeLLM:
    """Scripted LLM: returns queued JSON responses per agent, based on system prompt."""

    def __init__(self, json_responses: dict[str, list[dict[str, Any]]]):
        # key: substring identifying the agent's system prompt -> list of responses
        self._responses = json_responses
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, model: str, system: str, prompt: str, max_tokens: int = 16000) -> str:
        self.calls.append({"model": model, "system": system, "prompt": prompt})
        return "ok"

    def complete_json(
        self, *, model: str, system: str, prompt: str, schema: dict, max_tokens: int = 16000
    ) -> dict[str, Any]:
        self.calls.append({"model": model, "system": system, "prompt": prompt})
        for key, queue in self._responses.items():
            if key in system:
                return queue.pop(0) if len(queue) > 1 else queue[0]
        raise AssertionError(f"No scripted response for system prompt: {system[:80]}")


SAMPLE_HITS = [
    {
        "chunk_id": 1,
        "document_id": 10,
        "document_title": "Справка о задолженности № КД-2024-11-458",
        "page": None,
        "section": "Текущая задолженность",
        "text": "Общая задолженность: 4 822 560,55 руб. по состоянию на 01.07.2026",
        "score": 0.92,
    },
]

SAMPLE_FACTS = [
    {
        "document_id": 10,
        "document_title": "Справка о задолженности № КД-2024-11-458",
        "amount": 56780.00,
        "currency": "RUB",
        "due_date": "2026-07-15",
        "description": "Ежемесячный аннуитетный платёж",
    },
]


@pytest.fixture
def fake_services():
    def make(llm: FakeLLM, min_confidence: int = 60) -> Services:
        return Services(
            llm=llm,
            retrieve=lambda q, c, f: SAMPLE_HITS,
            fetch_structured=lambda c, f: SAMPLE_FACTS,
            min_confidence=min_confidence,
        )

    return make
