"""Document library: ingest (parse -> categorize -> extract -> chunk -> embed -> store),
browse, view, download original, delete."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.ingestion.categorizer import categorize
from app.ingestion.chunker import chunk_markdown
from app.ingestion.entities import extract
from app.ingestion.parser import parse_to_markdown
from app.llm.anthropic_client import get_llm
from app.llm.embeddings import get_embedder
from app.schemas import DocumentDetail, DocumentInfo, EntityInfo, IngestResult, PaymentInfo
from app.storage import files, graph
from app.storage.db import get_db
from app.storage.models import Chunk, Document, Entity, Payment

router = APIRouter()


def _info(d: Document) -> DocumentInfo:
    return DocumentInfo(
        id=d.id,
        title=d.title,
        category=d.category,
        family_member=d.family_member,
        source_filename=d.source_filename,
        size_bytes=d.size_bytes,
        created_at=d.created_at,
    )


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
        stored_path=files.save_upload(file.filename or "upload", content),
        mime_type=file.content_type,
        size_bytes=len(content),
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
def list_documents(
    category: str | None = None,
    family_member: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[DocumentInfo]:
    query = db.query(Document)
    if category:
        query = query.filter(Document.category == category)
    if family_member:
        query = query.filter(Document.family_member == family_member)
    if q:
        query = query.filter(Document.title.ilike(f"%{q}%"))
    docs = query.order_by(Document.created_at.desc()).limit(200).all()
    return [_info(d) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentDetail:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail(
        **_info(document).model_dump(),
        markdown=document.raw_markdown,
        entities=[
            EntityInfo(kind=e.kind, value=e.value, normalized=e.normalized)
            for e in document.entities
        ],
        payments=[
            PaymentInfo(
                amount=float(p.amount),
                currency=p.currency,
                due_date=p.due_date,
                description=p.description,
            )
            for p in document.payments
        ],
    )


@router.get("/documents/{document_id}/file")
def download_document(document_id: int, db: Session = Depends(get_db)) -> FileResponse:
    document = db.get(Document, document_id)
    if document is None or not document.stored_path:
        raise HTTPException(status_code=404, detail="Original file not found")
    path = files.resolve(document.stored_path)
    if path is None:
        raise HTTPException(status_code=404, detail="Original file is missing on disk")
    return FileResponse(
        path,
        media_type=document.mime_type or "application/octet-stream",
        filename=document.source_filename or path.name,
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    for model in (Chunk, Entity, Payment):
        db.query(model).filter(model.document_id == document_id).delete()
    if document.stored_path:
        files.delete(document.stored_path)
    db.delete(document)
    db.flush()
    graph.delete_document(document_id)
