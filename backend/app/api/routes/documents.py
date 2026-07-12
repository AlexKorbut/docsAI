"""Document library. Primary ingestion path: photos of paper documents (several
photos = pages of one document, transcribed by Claude vision). Electronic files
(.pdf/.txt/.md) are the secondary path."""

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.ingestion import jobs
from app.ingestion.chunker import chunk_markdown
from app.ingestion.entities import extract
from app.ingestion.pipeline import UploadItem
from app.llm.anthropic_client import get_llm
from app.llm.embeddings import get_embedder
from app.schemas import (
    DocumentDetail,
    DocumentInfo,
    DocumentUpdate,
    EntityInfo,
    FileInfo,
    JobAccepted,
    MarkdownUpdate,
    PaymentInfo,
)
from app.storage import files, graph
from app.storage.db import get_db
from app.storage.models import Chunk, Document, DocumentFile, Entity, Payment

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


async def _read_items(uploads: list[UploadFile]) -> list[UploadItem]:
    return [
        UploadItem(
            filename=u.filename or "upload",
            content=await u.read(),
            content_type=u.content_type,
        )
        for u in uploads
    ]


@router.post("/documents", response_model=JobAccepted, status_code=202)
async def upload_document(
    background: BackgroundTasks,
    uploads: list[UploadFile] = File(alias="files"),
    family_member: str | None = None,
    db: Session = Depends(get_db),
) -> JobAccepted:
    """Enqueue ingestion of ONE document (photos of its pages, or one e-file).

    Recognition takes up to minutes, so it runs in the background — poll
    GET /api/jobs/{job_id} for progress and the result."""
    items = await _read_items(uploads)
    try:
        job_id = jobs.enqueue(db, "single", items, family_member)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background.add_task(jobs.run_job, job_id)
    return JobAccepted(job_id=job_id)


@router.post("/documents/batch", response_model=JobAccepted, status_code=202)
async def upload_batch(
    background: BackgroundTasks,
    uploads: list[UploadFile] = File(alias="files"),
    family_member: str | None = None,
    db: Session = Depends(get_db),
) -> JobAccepted:
    """Enqueue a scanner batch: a stack of DIFFERENT documents scanned page-by-page.

    Pages are transcribed one-by-one, boundaries detected, and every document
    saved separately — poll GET /api/jobs/{job_id} for per-page progress."""
    items = await _read_items(uploads)
    try:
        job_id = jobs.enqueue(db, "batch", items, family_member)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background.add_task(jobs.run_job, job_id)
    return JobAccepted(job_id=job_id)


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
        files=[
            FileInfo(
                id=f.id,
                filename=f.filename,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes,
                position=f.position,
            )
            for f in document.files
        ],
    )


def _serve(document: Document, record: DocumentFile) -> FileResponse:
    path = files.resolve(record.stored_path)
    if path is None:
        raise HTTPException(status_code=404, detail="Original file is missing on disk")
    return FileResponse(
        path,
        media_type=record.mime_type or "application/octet-stream",
        filename=record.filename,
    )


@router.get("/documents/{document_id}/file")
def download_first_file(document_id: int, db: Session = Depends(get_db)) -> FileResponse:
    document = db.get(Document, document_id)
    if document is None or not document.files:
        raise HTTPException(status_code=404, detail="Original file not found")
    return _serve(document, document.files[0])


@router.get("/documents/{document_id}/files/{file_id}")
def download_file(document_id: int, file_id: int, db: Session = Depends(get_db)) -> FileResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    record = next((f for f in document.files if f.id == file_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    return _serve(document, record)


@router.patch("/documents/{document_id}", response_model=DocumentInfo)
def update_document(
    document_id: int, update: DocumentUpdate, db: Session = Depends(get_db)
) -> DocumentInfo:
    """Fix metadata the categorizer got wrong: title, category, family member."""
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if update.title is not None:
        document.title = update.title
    if update.category is not None:
        document.category = update.category
    if update.family_member is not None:
        document.family_member = update.family_member or None
    db.flush()
    graph.sync_document(document.id, document.title, document.category, [])
    return _info(document)


@router.put("/documents/{document_id}/markdown", response_model=DocumentDetail)
def update_markdown(
    document_id: int, update: MarkdownUpdate, db: Session = Depends(get_db)
) -> DocumentDetail:
    """Fix the recognized text: replaces the markdown and re-runs extraction,
    chunking and embeddings so search and payments reflect the correction."""
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    llm = get_llm()
    entities, payments = extract(update.markdown, llm)
    chunks = chunk_markdown(update.markdown)
    embeddings = get_embedder().embed_documents([c.text for c in chunks]) if chunks else []

    for model in (Chunk, Entity, Payment):
        db.query(model).filter(model.document_id == document_id).delete()
    document.raw_markdown = update.markdown

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
    graph.sync_document(
        document.id, document.title, document.category, [e.model_dump() for e in entities]
    )
    db.expire(document)
    return get_document(document_id, db)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    for record in document.files:
        files.delete(record.stored_path)
    for model in (DocumentFile, Chunk, Entity, Payment):
        db.query(model).filter(model.document_id == document_id).delete()
    if document.stored_path:  # legacy single-file column
        files.delete(document.stored_path)
    db.delete(document)
    db.flush()
    graph.delete_document(document_id)
