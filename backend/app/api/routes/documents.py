"""Document ingestion pipeline: parse -> categorize -> extract -> chunk -> embed -> store."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ingestion.categorizer import categorize
from app.ingestion.chunker import chunk_markdown
from app.ingestion.entities import extract
from app.ingestion.parser import parse_to_markdown
from app.llm.anthropic_client import get_llm
from app.llm.embeddings import get_embedder
from app.schemas import DocumentInfo, IngestResult
from app.storage import graph
from app.storage.db import get_db
from app.storage.models import Chunk, Document, Entity, Payment

router = APIRouter()


@router.post("/documents", response_model=IngestResult)
async def upload_document(
    file: UploadFile,
    family_member: str | None = None,
    db: Session = Depends(get_db),
) -> IngestResult:
    content = await file.read()
    try:
        markdown = parse_to_markdown(file.filename or "upload", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    llm = get_llm()
    category, title = categorize(markdown, llm)
    entities, payments = extract(markdown, llm)

    document = Document(
        title=title,
        category=category,
        family_member=family_member,
        source_filename=file.filename,
        raw_markdown=markdown,
    )
    db.add(document)
    db.flush()

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
    )


@router.get("/documents", response_model=list[DocumentInfo])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentInfo]:
    docs = db.query(Document).order_by(Document.created_at.desc()).limit(200).all()
    return [
        DocumentInfo(id=d.id, title=d.title, category=d.category, created_at=d.created_at)
        for d in docs
    ]
