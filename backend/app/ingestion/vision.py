"""Photo -> Markdown transcription via Claude vision.

This is the primary ingestion path: users photograph paper documents (medical
records, receipts, statements) and upload several photos as pages of one document.
"""

from app.config import get_settings
from app.ingestion.images import to_base64_jpeg
from app.llm.anthropic_client import LLMClient

ILLEGIBLE_MARKER = "[неразборчиво]"

SYSTEM = f"""You transcribe photographed paper documents (medical records, utility
bills, loan statements, warranties — usually in Russian) into Markdown, verbatim.

Rules:
- Transcribe EXACTLY what is written: never paraphrase, translate, or "fix" the text.
- Copy every number, date, name, and amount character-for-character — these are used
  for financial and medical decisions, accuracy is critical.
- Preserve document structure: headings as #/##, tables as Markdown tables, lists
  as lists. Include stamps, signatures notes as (печать), (подпись).
- Handwritten text: transcribe it; if a fragment cannot be read confidently, write
  {ILLEGIBLE_MARKER} instead of guessing.
- Multiple photos are pages of ONE document, in order. Start each page with
  "## Страница N" when there is more than one photo.
- Output ONLY the Markdown transcription, no commentary."""


def transcribe_page(photo: bytes, llm: LLMClient) -> str:
    """Transcribe a single scanned page (batch/scanner mode transcribes per page
    so one bad page cannot degrade or truncate the whole stack)."""
    return llm.complete_vision(
        model=get_settings().vision_model,
        system=SYSTEM,
        prompt="Transcribe this single page to Markdown.",
        images=[to_base64_jpeg(photo)],
    )


def illegible_warnings(markdown: str) -> list[str]:
    illegible = markdown.count(ILLEGIBLE_MARKER)
    if not illegible:
        return []
    return [
        f"Не удалось распознать {illegible} фрагмент(ов) — проверьте документ "
        "и при необходимости переснимите страницы при лучшем освещении."
    ]


def transcribe_photos(photos: list[bytes], llm: LLMClient) -> tuple[str, list[str]]:
    """Transcribe document photos to Markdown. Returns (markdown, warnings)."""
    images = [to_base64_jpeg(content) for content in photos]
    prompt = f"Transcribe this document ({len(images)} photo(s) = pages, in order) to Markdown."
    markdown = llm.complete_vision(
        model=get_settings().vision_model,
        system=SYSTEM,
        prompt=prompt,
        images=images,
    )
    return markdown, illegible_warnings(markdown)
