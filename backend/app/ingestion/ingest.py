"""Shared persistence step: markdown + original files -> full document record."""

from sqlalchemy.orm import Session

from app.ingestion.categorizer import categorize
from app.ingestion.chunker import chunk_markdown
from app.ingestion.entities import extract
from app.ingestion.pipeline import UploadItem
from app.llm.anthropic_client import LLMClient
from app.llm.embeddings import get_embedder
from app.schemas import IngestResult
from app.storage import files, graph
from app.storage.models import Chunk, Document, DocumentFile, Entity, Payment


def ingest_document(
    markdown: str,
    items: list[UploadItem],
    family_member: str | None,
    warnings: list[str],
    llm: LLMClient,
    db: Session,
) -> IngestResult:
    """Categorize, extract, embed and persist one document with its original files."""
    category, title = categorize(markdown, llm)
    entities, payments = extract(markdown, llm)

    document = Document(
        title=title,
        category=category,
        family_member=family_member,
        source_filename=items[0].filename,
        size_bytes=sum(len(i.content) for i in items),
        raw_markdown=markdown,
    )
    db.add(document)
    db.flush()

    for position, item in enumerate(items):
        db.add(
            DocumentFile(
                document_id=document.id,
                position=position,
                filename=item.filename,
                stored_path=files.save_upload(item.filename, item.content),
                mime_type=item.content_type,
                size_bytes=len(item.content),
            )
        )

    chunks = chunk_markdown(markdown)
    embeddings = get_embedder().embed_documents([c.text for c in chunks]) if chunks else []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        db.add(
            Chunk(
                document_id=document.id,
                section=chunk.section,
                page=chunk.page,
                text=chunk.text,
                embedding=embedding,
            )
        )
    for e in entities:
        db.add(Entity(document_id=document.id, kind=e.kind, value=e.value, normalized=e.normalized))
    for p in payments:
        db.add(
            Payment(
                document_id=document.id,
                amount=p.amount,
                currency=p.currency,
                due_date=p.due_date,
                description=p.description,
            )
        )
    db.flush()

    graph.sync_document(document.id, title, category, [e.model_dump() for e in entities])

    return IngestResult(
        document_id=document.id,
        title=title,
        category=category,
        chunks=len(chunks),
        entities=len(entities),
        payments=len(payments),
        pages=len(items),
        warnings=warnings,
    )
