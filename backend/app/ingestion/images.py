"""Photo preprocessing for vision transcription.

Phone photos arrive rotated (EXIF), oversized, and often in HEIC. Normalize
everything to upright JPEG capped at MAX_EDGE px on the long side — Claude's
high-resolution vision limit is 2576px, and this keeps token costs bounded.
"""

import base64
import io
from pathlib import Path

import pillow_heif
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

MAX_EDGE = 2048
JPEG_QUALITY = 88

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff"}


def is_image(filename: str, content_type: str | None = None) -> bool:
    if content_type and content_type.startswith("image/"):
        return True
    return Path(filename).suffix.lower() in IMAGE_SUFFIXES


def preprocess(content: bytes) -> bytes:
    """Return upright, resized JPEG bytes. Raises ValueError on unreadable images."""
    try:
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image)
    except Exception as exc:
        raise ValueError("Не удалось прочитать изображение") from exc

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    longest = max(image.size)
    if longest > MAX_EDGE:
        scale = MAX_EDGE / longest
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)), Image.LANCZOS
        )

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue()


def to_base64_jpeg(content: bytes) -> tuple[str, str]:
    """Preprocess and return (media_type, base64_data) ready for the vision API."""
    return "image/jpeg", base64.standard_b64encode(preprocess(content)).decode("ascii")
