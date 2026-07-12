"""Original-file storage: uploads are kept verbatim on disk next to the DB record."""

import re
import uuid
from pathlib import Path

from app.config import get_settings


def _safe_name(filename: str) -> str:
    name = Path(filename).name  # strip any path components
    name = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE)
    return name[-200:] or "upload"


def save_upload(filename: str, content: bytes) -> str:
    """Persist the original bytes; returns the path (relative to upload_dir)."""
    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    relative = f"{uuid.uuid4().hex[:12]}_{_safe_name(filename)}"
    (upload_dir / relative).write_bytes(content)
    return relative


def resolve(stored_path: str) -> Path | None:
    """Resolve a stored path back to a file, refusing anything outside upload_dir."""
    upload_dir = Path(get_settings().upload_dir).resolve()
    candidate = (upload_dir / stored_path).resolve()
    if not candidate.is_relative_to(upload_dir) or not candidate.is_file():
        return None
    return candidate


def delete(stored_path: str) -> None:
    candidate = resolve(stored_path)
    if candidate is not None:
        candidate.unlink(missing_ok=True)
