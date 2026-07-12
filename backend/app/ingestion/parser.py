"""Document parsing: PDF/scans -> Markdown.

Priority: LlamaParse (if LLAMAPARSE_API_KEY set, best for tables) -> Docling (local)
-> plain text passthrough for .txt/.md. The demo path uses .md/.txt samples so the
project works without heavy parser dependencies installed.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


def parse_to_markdown(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix in TEXT_SUFFIXES:
        return content.decode("utf-8", errors="replace")

    # TODO: LlamaParse integration when LLAMAPARSE_API_KEY is configured.

    try:
        return _parse_with_docling(filename, content)
    except ImportError as exc:
        raise ValueError(
            f"Cannot parse '{filename}': install the 'parsing' extra "
            '(pip install -e ".[parsing]") for PDF/scan support, '
            "or upload .txt/.md files."
        ) from exc


def _parse_with_docling(filename: str, content: bytes) -> str:
    import tempfile

    from docling.document_converter import DocumentConverter

    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    result = DocumentConverter().convert(tmp_path)
    return result.document.export_to_markdown()
