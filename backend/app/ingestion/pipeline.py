"""Upload -> Markdown: routes photos to vision transcription (the primary path)
and electronic documents to the file parser."""

from dataclasses import dataclass

from app.ingestion.images import is_image
from app.ingestion.parser import parse_to_markdown
from app.ingestion.vision import transcribe_photos
from app.llm.anthropic_client import LLMClient

MAX_PHOTOS = 20
MAX_FILE_BYTES = 30 * 1024 * 1024


@dataclass
class UploadItem:
    filename: str
    content: bytes
    content_type: str | None = None


def to_markdown(uploads: list[UploadItem], llm: LLMClient) -> tuple[str, list[str]]:
    """Convert an upload batch to Markdown. Returns (markdown, warnings).

    A batch is either photos of one paper document (any count, treated as pages)
    or exactly one electronic document (.pdf/.txt/.md).
    """
    if not uploads:
        raise ValueError("Файлы не переданы")
    for item in uploads:
        if len(item.content) > MAX_FILE_BYTES:
            raise ValueError(f"Файл «{item.filename}» больше 30 МБ")

    image_flags = [is_image(item.filename, item.content_type) for item in uploads]

    if all(image_flags):
        if len(uploads) > MAX_PHOTOS:
            raise ValueError(f"Не больше {MAX_PHOTOS} фото за одну загрузку")
        return transcribe_photos([item.content for item in uploads], llm)

    if any(image_flags):
        raise ValueError(
            "Смешанная загрузка не поддерживается: либо фото одного документа, "
            "либо один электронный файл"
        )

    if len(uploads) > 1:
        raise ValueError("Электронные документы загружаются по одному")

    return parse_to_markdown(uploads[0].filename, uploads[0].content), []
