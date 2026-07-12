"""Upload -> Markdown: routes photos to vision transcription (the primary path)
and electronic documents to the file parser."""

from dataclasses import dataclass

from app.ingestion.images import is_image
from app.ingestion.parser import parse_to_markdown
from app.ingestion.vision import transcribe_photos
from app.llm.anthropic_client import LLMClient

MAX_PHOTOS = 20
MAX_BATCH_PAGES = 60
MAX_FILE_BYTES = 30 * 1024 * 1024


@dataclass
class UploadItem:
    filename: str
    content: bytes
    content_type: str | None = None


@dataclass
class StoredUpload:
    """An original file already persisted to the upload dir."""

    filename: str
    stored_path: str
    content_type: str | None = None
    size_bytes: int = 0


def _check_sizes(uploads: list[UploadItem]) -> None:
    if not uploads:
        raise ValueError("Файлы не переданы")
    for item in uploads:
        if len(item.content) > MAX_FILE_BYTES:
            raise ValueError(f"Файл «{item.filename}» больше 30 МБ")


def validate_single(uploads: list[UploadItem]) -> None:
    """One document per upload: photos of one paper document, or one e-file."""
    _check_sizes(uploads)
    image_flags = [is_image(item.filename, item.content_type) for item in uploads]
    if all(image_flags):
        if len(uploads) > MAX_PHOTOS:
            raise ValueError(f"Не больше {MAX_PHOTOS} фото за одну загрузку")
        return
    if any(image_flags):
        raise ValueError(
            "Смешанная загрузка не поддерживается: либо фото одного документа, "
            "либо один электронный файл"
        )
    if len(uploads) > 1:
        raise ValueError("Электронные документы загружаются по одному")


def validate_batch(uploads: list[UploadItem]) -> None:
    """Scanner batch: images only, page-per-file."""
    _check_sizes(uploads)
    if len(uploads) > MAX_BATCH_PAGES:
        raise ValueError(f"Не больше {MAX_BATCH_PAGES} страниц за одну пачку")
    for item in uploads:
        if not is_image(item.filename, item.content_type):
            raise ValueError("Пакетный режим принимает только изображения (сканы страниц)")


def to_markdown(uploads: list[UploadItem], llm: LLMClient) -> tuple[str, list[str]]:
    """Convert a single-document upload batch to Markdown. Returns (markdown, warnings)."""
    validate_single(uploads)
    if all(is_image(item.filename, item.content_type) for item in uploads):
        return transcribe_photos([item.content for item in uploads], llm)
    return parse_to_markdown(uploads[0].filename, uploads[0].content), []
