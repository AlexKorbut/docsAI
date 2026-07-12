"""Photo ingestion path: preprocessing, vision transcription, and batch routing."""

import io

import pytest
from PIL import Image

from app.ingestion.images import MAX_EDGE, is_image, preprocess
from app.ingestion.pipeline import UploadItem, to_markdown
from app.ingestion.vision import ILLEGIBLE_MARKER
from tests.conftest import FakeLLM


def make_photo(width: int = 800, height: int = 600, fmt: str = "JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(200, 180, 150)).save(buffer, format=fmt)
    return buffer.getvalue()


# --- images.py ---


def test_is_image_by_extension_and_content_type() -> None:
    assert is_image("scan.jpg")
    assert is_image("scan.HEIC")
    assert is_image("photo", content_type="image/png")
    assert not is_image("report.pdf")
    assert not is_image("notes.md", content_type="text/markdown")


def test_preprocess_resizes_oversized_photos() -> None:
    processed = preprocess(make_photo(width=MAX_EDGE * 2, height=MAX_EDGE))
    image = Image.open(io.BytesIO(processed))
    assert max(image.size) == MAX_EDGE
    assert image.format == "JPEG"


def test_preprocess_converts_png_to_jpeg() -> None:
    processed = preprocess(make_photo(fmt="PNG"))
    assert Image.open(io.BytesIO(processed)).format == "JPEG"


def test_preprocess_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        preprocess(b"not an image at all")


# --- pipeline.py ---


def test_photos_go_through_vision() -> None:
    llm = FakeLLM(vision_response="# Выписка\n\nтекст со снимка")
    photos = [
        UploadItem("page1.jpg", make_photo()),
        UploadItem("page2.jpg", make_photo()),
    ]
    markdown, warnings = to_markdown(photos, llm)
    assert "текст со снимка" in markdown
    assert warnings == []
    assert llm.calls[0]["images"] == 2


def test_illegible_fragments_produce_warning() -> None:
    llm = FakeLLM(vision_response=f"# Документ\n\nсумма {ILLEGIBLE_MARKER} руб.")
    markdown, warnings = to_markdown([UploadItem("scan.jpg", make_photo())], llm)
    assert ILLEGIBLE_MARKER in markdown
    assert len(warnings) == 1
    assert "переснимите" in warnings[0]


def test_electronic_document_bypasses_vision() -> None:
    llm = FakeLLM()
    markdown, warnings = to_markdown([UploadItem("note.md", "# Заголовок".encode())], llm)
    assert markdown == "# Заголовок"
    assert warnings == []
    assert llm.calls == []


def test_mixed_batch_is_rejected() -> None:
    with pytest.raises(ValueError, match="Смешанная"):
        to_markdown(
            [UploadItem("scan.jpg", make_photo()), UploadItem("note.md", b"x")],
            FakeLLM(),
        )


def test_multiple_electronic_documents_rejected() -> None:
    with pytest.raises(ValueError, match="по одному"):
        to_markdown([UploadItem("a.md", b"x"), UploadItem("b.md", b"y")], FakeLLM())


def test_empty_batch_rejected() -> None:
    with pytest.raises(ValueError):
        to_markdown([], FakeLLM())
