"""Background ingestion jobs.

Recognition of a photo batch takes minutes, far beyond HTTP timeouts, so uploads
are two-phase: the request stores originals on disk and creates an `ingest_jobs`
row (fast), then a background task runs recognition and updates the row. Clients
poll GET /api/jobs/{id}.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.ingestion.images import is_image
from app.ingestion.ingest import ingest_document
from app.ingestion.pipeline import (
    StoredUpload,
    UploadItem,
    to_markdown,
    validate_batch,
    validate_single,
)
from app.ingestion.splitter import count_documents, detect_boundaries
from app.ingestion.vision import illegible_warnings, transcribe_page
from app.llm.anthropic_client import get_llm
from app.storage import files
from app.storage.db import get_session_factory
from app.storage.models import IngestJob

logger = logging.getLogger(__name__)


def enqueue(db: Session, kind: str, items: list[UploadItem], family_member: str | None) -> str:
    """Validate, persist originals, create the job row. Returns job id."""
    if kind == "batch":
        validate_batch(items)
    else:
        validate_single(items)

    stored = [
        {
            "filename": item.filename,
            "stored_path": files.save_upload(item.filename, item.content),
            "content_type": item.content_type,
            "size_bytes": len(item.content),
        }
        for item in items
    ]
    job = IngestJob(
        id=uuid.uuid4().hex,
        kind=kind,
        status="pending",
        family_member=family_member,
        files=stored,
        progress_total=len(stored),
    )
    db.add(job)
    db.flush()
    return job.id


def _load_items(job: IngestJob) -> list[UploadItem]:
    items = []
    for record in job.files:
        path = files.resolve(record["stored_path"])
        if path is None:
            raise ValueError(f"Файл «{record['filename']}» пропал с диска")
        items.append(
            UploadItem(
                filename=record["filename"],
                content=path.read_bytes(),
                content_type=record.get("content_type"),
            )
        )
    return items


def _stored(job: IngestJob, indices: list[int] | None = None) -> list[StoredUpload]:
    records = job.files if indices is None else [job.files[i] for i in indices]
    return [
        StoredUpload(
            filename=r["filename"],
            stored_path=r["stored_path"],
            content_type=r.get("content_type"),
            size_bytes=r.get("size_bytes", 0),
        )
        for r in records
    ]


def run_job(job_id: str) -> None:
    """Executed by a background task; owns its DB session."""
    session = get_session_factory()()
    try:
        job = session.get(IngestJob, job_id)
        if job is None or job.status not in ("pending",):
            return
        job.status = "processing"
        session.commit()
        try:
            result = _run_single(job, session) if job.kind == "single" else _run_batch(job, session)
            job.result = result
            job.status = "done"
            job.progress_done = job.progress_total
        except Exception as exc:
            logger.exception("Ingest job %s failed", job_id)
            session.rollback()
            job = session.get(IngestJob, job_id)
            job.status = "error"
            job.error = str(exc) or exc.__class__.__name__
        session.commit()
    finally:
        session.close()


def _run_single(job: IngestJob, session: Session) -> dict:
    llm = get_llm()
    items = _load_items(job)
    markdown, warnings = to_markdown(items, llm)

    # Guardrail: one upload must be ONE document — warn loudly if it isn't.
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
    result = ingest_document(markdown, _stored(job), job.family_member, warnings, llm, session)
    return result.model_dump()


def _run_batch(job: IngestJob, session: Session) -> dict:
    llm = get_llm()
    items = _load_items(job)
    batch_warnings: list[str] = []

    # 1. Per-page transcription — one bad page cannot degrade the whole stack.
    # TODO: parallelize page transcription.
    page_markdowns: list[str] = []
    for index, item in enumerate(items):
        page_markdowns.append(transcribe_page(item.content, llm))
        job.progress_done = index + 1
        session.commit()

    # 2. Boundary detection (contiguity enforced in the splitter).
    groups = detect_boundaries(page_markdowns, llm)

    # 3. Ingest each detected document independently.
    results = []
    for group in groups:
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
                    markdown,
                    _stored(job, group),
                    job.family_member,
                    illegible_warnings(markdown),
                    llm,
                    session,
                ).model_dump()
            )
            session.commit()
        except Exception:  # noqa: BLE001 — report per-group, keep going
            logger.exception("Batch group %s failed in job %s", group, job.id)
            session.rollback()
            pages = ", ".join(str(i + 1) for i in group)
            batch_warnings.append(f"Страницы {pages}: не удалось сохранить документ")

    if len(results) > 1:
        batch_warnings.append(
            "Границы документов определены автоматически — проверьте результат "
            "в библиотеке; ошибочно склеенные или разрезанные документы удалите "
            "и загрузите заново по отдельности."
        )
    return {"documents": results, "warnings": batch_warnings}
