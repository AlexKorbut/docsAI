"""Split markdown into section-aware chunks for embedding."""

from dataclasses import dataclass

MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 150


@dataclass
class TextChunk:
    text: str
    section: str | None = None
    page: int | None = None


def chunk_markdown(markdown: str) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        buffer.clear()
        if not text:
            return
        for piece in _split_long(text):
            chunks.append(TextChunk(text=piece, section=section))

    for line in markdown.splitlines():
        if line.startswith("#"):
            flush()
            section = line.lstrip("#").strip() or section
            continue
        buffer.append(line)
        if sum(len(x) for x in buffer) > MAX_CHUNK_CHARS * 2:
            flush()
    flush()
    return chunks


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    pieces = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHUNK_CHARS, len(text))
        pieces.append(text[start:end])
        if end == len(text):
            break
        start = end - OVERLAP_CHARS
    return pieces
