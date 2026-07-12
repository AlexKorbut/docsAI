"""Ingestion job status: clients poll this after POST /api/documents[/batch]."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import JobOut, JobProgress
from app.storage.db import get_db
from app.storage.models import IngestJob

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(IngestJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(
        id=job.id,
        kind=job.kind,
        status=job.status,
        progress=JobProgress(done=job.progress_done, total=job.progress_total),
        result=job.result,
        error=job.error,
        created_at=job.created_at,
    )
