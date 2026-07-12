"""Shared state and service container for the LangGraph pipeline."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypedDict

from app.llm.anthropic_client import LLMClient


class SourceDict(TypedDict, total=False):
    document_id: int
    document_title: str
    page: int | None
    section: str | None
    snippet: str


class AgentState(TypedDict, total=False):
    # Input
    question: str
    category: str | None
    family_member: str | None
    query_id: str

    # Planner
    plan: list[str]
    search_queries: list[str]

    # Retriever
    hits: list[dict[str, Any]]

    # Structured Query
    structured_facts: list[dict[str, Any]]

    # Calculator
    calculations: list[str]

    # Reasoner
    draft: str
    draft_sources: list[SourceDict]

    # Verifier
    confidence: int
    issues: list[str]
    retry_count: int

    # Output
    answer: str
    sources: list[SourceDict]
    warnings: list[str]


@dataclass
class Services:
    """Injected dependencies — swap for fakes in tests."""

    llm: LLMClient
    # (query, category, family_member) -> list of hit dicts
    retrieve: Callable[[str, str | None, str | None], list[dict[str, Any]]]
    # (category, family_member) -> list of exact payment/entity fact dicts
    fetch_structured: Callable[[str | None, str | None], list[dict[str, Any]]]
    # (query_id, agent, payload) -> None  — audit log
    audit: Callable[[str, str, dict[str, Any]], None] = field(
        default=lambda *_: None  # type: ignore[assignment]
    )
    min_confidence: int = 60
    max_retries: int = 1
