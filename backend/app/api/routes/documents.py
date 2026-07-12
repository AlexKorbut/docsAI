"""Document library. Primary ingestion path: photos of paper documents (several
photos = pages of one document, transcribed by Claude vision). Electronic files
(.pdf/.txt/.md) are the secondary path."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.ingestion.images import is_image
from app.ingestion.ingest import ingest_document
from app.ingestion.pipeline import MAX_FILE_BYTES, UploadItem, to_markdown
from app.ingestion.splitter import count_documents, detect_boundaries
from app.ingestion.vision import illegible_warnings, transcribe_page
from app.llm.anthropic_client import get_llm
from app.schemas import (
    BatchIngestResult,
    DocumentDetail,
    DocumentInfo,
    EntityInfo,
    FileInfo,
    IngestResult,
    PaymentInfo,
)
from app.storage import files, graph
from app.storage.db import get_db
from app.storage.models import Chunk, Document, DocumentFile, Entity, Payment

MAX_BATCH_PAGES = 60

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
    uploads: list[UploadFile] = File(alias="files"),
    family_member: str | None = None,
    db: Session = Depends(get_db),
) -> IngestResult:
    items = [
        UploadItem(
            filename=u.filename or "upload",
            content=await u.read(),
            content_type=u.content_type,
        )
        for u in uploads
    ]

    llm = get_llm()
    try:
        markdown, warnings = to_markdown(items, llm)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Guardrail: one upload must be ONE document. If the transcription clearly
    # contains several unrelated documents, save anyway but warn loudly.
    if any(is_image(i.filename, i.content_type) for i in items):
        found = count_documents(markdown, llm)
        if found > 1:
            warnings.insert(
                0,
                f"Похоже, в этой загрузке {found} разных документа(ов). "
                "Один документ = одна загрузка; для пачки со сканера используйте "
                "пакетный режим («Пачка со сканера»). Рекомендуем удалить эту запись "
                "и загрузить документы по отдельности.",
            )

    return ingest_document(markdown, items, family_member, warnings, llm, db)


@router.post("/documents/batch", response_model=BatchIngestResult)
async def upload_batch(
    uploads: list[UploadFile] = File(alias="files"),
    family_member: str | None = None,
    db: Session = Depends(get_db),
) -> BatchIngestResult:
    """Scanner-batch mode: a stack of DIFFERENT paper documents scanned page-by-page.

    Each page is transcribed separately, an LLM detects document boundaries
    (contiguous pages only), and every detected document is saved on its own.
    """
    items = [
        UploadItem(
            filename=u.filename or "upload",
            content=await u.read(),
            content_type=u.content_type,
        )
        for u in uploads
    ]
    if not items:
        raise HTTPException(status_code=422, detail="Файлы не переданы")
    if len(items) > MAX_BATCH_PAGES:
        raise HTTPException(
            status_code=422, detail=f"Не больше {MAX_BATCH_PAGES} страниц за одну пачку"
        )
    for item in items:
        if not is_image(item.filename, item.content_type):
            raise HTTPException(
                status_code=422,
                detail="Пакетный режим принимает только изображения (сканы страниц)",
            )
        if len(item.content) > MAX_FILE_BYTES:
            raise HTTPException(status_code=422, detail=f"Файл «{item.filename}» больше 30 МБ")

    llm = get_llm()
    batch_warnings: list[str] = []

    # 1. Per-page transcription — one bad page cannot degrade the whole stack.
    # TODO: parallelize page transcription.
    page_markdowns: list[str] = []
    for item in items:
        try:
            page_markdowns.append(transcribe_page(item.content, llm))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"«{item.filename}»: {exc}") from exc

    # 2. Boundary detection over page texts (contiguity enforced in the splitter).
    groups = detect_boundaries(page_markdowns, llm)

    # 3. Ingest each detected document independently; one failure doesn't kill the rest.
    results: list[IngestResult] = []
    for group in groups:
        group_items = [items[i] for i in group]
        pages_md = [page_markdowns[i] for i in group]
        if len(pages_md) > 1:
            markdown = "\n\n".join(
                f"## Страница {n + 1}\n\n{text}" for n, text in enumerate(pages_md)
            )
        else:
            markdown = pages_md[0]
        try:
            results.append(
                ingest_document(
                    markdown, group_items, family_member, illegible_warnings(markdown), llm, db
                )
            )
        except Exception:  # noqa: BLE001 — report per-group, keep going
            page_numbers = ", ".join(str(i + 1) for i in group)
            batch_warnings.append(f"Страницы {page_numbers}: не удалось сохранить документ")

    if len(results) > 1:
        batch_warnings.append(
            "Границы документов определены автоматически — проверьте результат "
            "в библиотеке; ошибочно склеенные или разрезанные документы удалите "
            "и загрузите заново по отдельности."
        )
    return BatchIngestResult(documents=results, warnings=batch_warnings)


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
