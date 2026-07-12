"""Boundary detection for scanner batches + the one-upload-one-document guardrail."""

from app.ingestion.splitter import count_documents, detect_boundaries
from tests.conftest import FakeLLM

SPLIT_KEY = "document-boundary detector"
COUNT_KEY = "exactly one"

PAGES = [
    "# Справка о задолженности\nБанк Пример",
    "продолжение таблицы платежей",
    "# Квитанция ЖКХ за июнь",
    "# Выписка из амбулаторной карты",
    "продолжение назначений",
]


def test_happy_path_three_documents() -> None:
    llm = FakeLLM(
        {
            SPLIT_KEY: [
                {
                    "documents": [
                        {"pages": [1, 2], "reason": "справка"},
                        {"pages": [3], "reason": "квитанция"},
                        {"pages": [4, 5], "reason": "медкарта"},
                    ]
                }
            ]
        }
    )
    assert detect_boundaries(PAGES, llm) == [[0, 1], [2], [3, 4]]


def test_malformed_groups_are_repaired_to_contiguous_cover() -> None:
    # LLM returns overlapping/non-contiguous nonsense; only group STARTS are
    # trusted, so the result is still a contiguous cover of all pages in order.
    llm = FakeLLM(
        {
            SPLIT_KEY: [
                {
                    "documents": [
                        {"pages": [1, 4], "reason": "рваная группа"},
                        {"pages": [3, 3], "reason": "дубль"},
                        {"pages": [99], "reason": "вне диапазона"},
                    ]
                }
            ]
        }
    )
    groups = detect_boundaries(PAGES, llm)
    assert groups == [[0, 1], [2, 3, 4]]
    flat = [i for g in groups for i in g]
    assert flat == list(range(len(PAGES)))


def test_single_page_needs_no_llm() -> None:
    llm = FakeLLM()
    assert detect_boundaries(["одна страница"], llm) == [[0]]
    assert detect_boundaries([], llm) == []
    assert llm.calls == []


def test_count_documents_detects_mixed_upload() -> None:
    llm = FakeLLM({COUNT_KEY: [{"document_count": 3}]})
    assert count_documents("# Справка\n...\n# Квитанция\n...\n# Гарантия", llm) == 3


def test_count_documents_falls_back_to_one_on_failure() -> None:
    assert count_documents("текст", FakeLLM()) == 1  # no scripted response -> exception -> 1
