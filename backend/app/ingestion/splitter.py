"""LLM document-boundary detection for scanner batches.

A stack of mixed paper documents scanned via an auto-feeder arrives as an ordered
sequence of page images. After per-page transcription, the splitter groups pages
into documents. Groups are always contiguous — the scanner preserves page order,
so any non-contiguous grouping from the LLM is repaired in code.
"""

from app.config import get_settings
from app.llm.anthropic_client import LLMClient

PAGE_PREVIEW_CHARS = 1500

SPLIT_SCHEMA = {
    "type": "object",
    "properties": {
        "documents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pages": {"type": "array", "items": {"type": "integer"}},
                    "reason": {"type": "string"},
                },
                "required": ["pages", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["documents"],
    "additionalProperties": False,
}

SPLIT_SYSTEM = """You are a document-boundary detector for a batch of scanned pages
(auto-feeder scanner, pages in order, usually Russian family documents: medical
records, utility bills, loan statements, warranties).

Given numbered page transcriptions, group pages into separate documents. Signals of
a NEW document: a letterhead or organization name at the top, a document title
("Справка", "Договор", "Квитанция", "Выписка"), a new document number or date,
an abrupt topic change. Signals of a CONTINUATION: "продолжение", page numbers > 1,
running tables, text that starts mid-sentence.

Rules:
- Every page belongs to exactly one document.
- Pages of one document are always consecutive (the scanner preserves order).
- When unsure, prefer keeping consecutive pages together.
- Give a short reason per document (its title or why the boundary is there)."""

COUNT_SCHEMA = {
    "type": "object",
    "properties": {"document_count": {"type": "integer"}},
    "required": ["document_count"],
    "additionalProperties": False,
}

COUNT_SYSTEM = """You check whether a transcription that SHOULD contain exactly one
document actually contains several unrelated ones (the user photographed different
papers in one upload by mistake). Count distinct documents: different organizations,
unrelated titles/numbers/topics. Pages of one multi-page document, its appendices
and attachments count as ONE document. Answer with the count only."""


def detect_boundaries(page_markdowns: list[str], llm: LLMClient) -> list[list[int]]:
    """Group page indices (0-based) into documents. Always returns contiguous groups
    that cover every page in order."""
    if len(page_markdowns) <= 1:
        return [[0]] if page_markdowns else []

    numbered = "\n\n".join(
        f"=== Страница {i + 1} ===\n{text[:PAGE_PREVIEW_CHARS]}"
        for i, text in enumerate(page_markdowns)
    )
    data = llm.complete_json(
        model=get_settings().extraction_model,
        system=SPLIT_SYSTEM,
        prompt=f"Pages ({len(page_markdowns)} total):\n\n{numbered}",
        schema=SPLIT_SCHEMA,
    )

    # The LLM speaks in 1-based page numbers; repair anything malformed.
    boundaries: set[int] = set()
    for doc in data.get("documents", []):
        pages = sorted(p - 1 for p in doc.get("pages", []) if 1 <= p <= len(page_markdowns))
        if pages:
            boundaries.add(pages[0])
    boundaries.add(0)

    starts = sorted(boundaries)
    groups = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(page_markdowns)
        groups.append(list(range(start, end)))
    return groups


def count_documents(markdown: str, llm: LLMClient) -> int:
    """Guardrail for the normal upload path: how many distinct documents does the
    transcription contain? Returns at least 1; falls back to 1 on any failure."""
    try:
        data = llm.complete_json(
            model=get_settings().extraction_model,
            system=COUNT_SYSTEM,
            prompt=f"Transcription:\n\n{markdown[:20000]}",
            schema=COUNT_SCHEMA,
        )
        return max(1, int(data["document_count"]))
    except Exception:
        return 1
