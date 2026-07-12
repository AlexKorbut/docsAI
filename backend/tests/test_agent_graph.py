"""End-to-end agent graph tests with a scripted LLM (no network, no DB)."""

from app.agents.graph import run_query
from tests.conftest import FakeLLM

PLANNER_KEY = "planning agent"
REASONER_KEY = "reasoning agent"
VERIFIER_KEY = "verification agent"

PLAN = {"steps": ["find loan docs", "sum amounts"], "search_queries": ["задолженность кредит"]}
DRAFT = {
    "answer": "Общая задолженность — 4 822 560,55 руб. (справка № КД-2024-11-458 от 01.07.2026).",
    "cited_chunk_ids": [1],
}


def test_happy_path_returns_verified_answer(fake_services) -> None:
    llm = FakeLLM(
        {
            PLANNER_KEY: [PLAN],
            REASONER_KEY: [DRAFT],
            VERIFIER_KEY: [{"confidence": 95, "issues": [], "corrected_answer": None}],
        }
    )
    state = run_query(fake_services(llm), "Сколько у нас долгов по кредитам?")

    assert "4 822 560,55" in state["answer"]
    assert state["confidence"] == 95
    assert state["warnings"] == []
    assert state["sources"][0]["document_id"] == 10
    assert "КД-2024-11-458" in state["sources"][0]["document_title"]


def test_low_confidence_triggers_retry_then_warns(fake_services) -> None:
    llm = FakeLLM(
        {
            PLANNER_KEY: [PLAN],
            REASONER_KEY: [DRAFT],
            VERIFIER_KEY: [
                {"confidence": 30, "issues": ["сумма не подтверждена"], "corrected_answer": None},
                {"confidence": 40, "issues": ["сумма не подтверждена"], "corrected_answer": None},
            ],
        }
    )
    state = run_query(fake_services(llm), "Сколько у нас долгов по кредитам?")

    # One retry happened (verifier called twice), then answer surfaced with warnings.
    assert state["confidence"] == 40
    assert any("Low confidence" in w for w in state["warnings"])
    assert any("сумма не подтверждена" in w for w in state["warnings"])


def test_verifier_correction_replaces_draft(fake_services) -> None:
    llm = FakeLLM(
        {
            PLANNER_KEY: [PLAN],
            REASONER_KEY: [DRAFT],
            VERIFIER_KEY: [
                {
                    "confidence": 90,
                    "issues": ["уточнена дата"],
                    "corrected_answer": "Исправленный ответ: 4 822 560,55 руб. на 01.07.2026.",
                }
            ],
        }
    )
    state = run_query(fake_services(llm), "Сколько у нас долгов по кредитам?")
    assert state["answer"].startswith("Исправленный ответ")
