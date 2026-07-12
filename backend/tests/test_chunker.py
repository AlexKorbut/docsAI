from app.ingestion.chunker import MAX_CHUNK_CHARS, chunk_markdown


def test_sections_become_chunk_metadata() -> None:
    md = "# Договор\nтекст раздела один\n\n## Платежи\nтекст раздела два"
    chunks = chunk_markdown(md)
    assert [c.section for c in chunks] == ["Договор", "Платежи"]


def test_long_text_is_split_with_overlap() -> None:
    md = "# S\n" + "а" * (MAX_CHUNK_CHARS * 3)
    chunks = chunk_markdown(md)
    assert len(chunks) >= 3
    assert all(len(c.text) <= MAX_CHUNK_CHARS for c in chunks)


def test_empty_document() -> None:
    assert chunk_markdown("") == []
