"""Pydantic request/response models for the API."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class IngestResult(BaseModel):
    document_id: int
    title: str
    category: str
    chunks: int
    entities: int
    payments: int
    pages: int = 1
    warnings: list[str] = []


class BatchIngestResult(BaseModel):
    """Scanner-batch upload: one upload produced several separate documents."""

    documents: list[IngestResult]
    warnings: list[str] = []


class JobAccepted(BaseModel):
    job_id: str


class JobProgress(BaseModel):
    done: int = 0
    total: int = 0


class JobOut(BaseModel):
    id: str
    kind: str  # single | batch
    status: str  # pending | processing | done | error
    progress: JobProgress
    # IngestResult (single) or BatchIngestResult (batch) once status == done
    result: dict | None = None
    error: str | None = None
    created_at: datetime


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    category: str | None = None
    family_member: str | None = None


class MarkdownUpdate(BaseModel):
    markdown: str = Field(min_length=1)


class DocumentInfo(BaseModel):
    id: int
    title: str
    category: str
    family_member: str | None = None
    source_filename: str | None = None
    size_bytes: int | None = None
    created_at: datetime


class EntityInfo(BaseModel):
    kind: str
    value: str
    normalized: str | None = None


class PaymentInfo(BaseModel):
    amount: float
    currency: str
    due_date: date | None = None
    description: str | None = None


class FileInfo(BaseModel):
    id: int
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = None
    position: int = 0


class DocumentDetail(DocumentInfo):
    markdown: str
    entities: list[EntityInfo]
    payments: list[PaymentInfo]
    files: list[FileInfo] = []


class FamilyMemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    relation: str | None = None
    birth_date: date | None = None
    notes: str | None = None


class FamilyMemberOut(FamilyMemberIn):
    id: int


class Reminder(BaseModel):
    document_id: int
    document_title: str
    category: str
    amount: float
    currency: str
    due_date: date
    description: str | None = None
    days_left: int


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    category: str | None = None
    family_member: str | None = None


class Source(BaseModel):
    document_id: int
    document_title: str
    page: int | None = None
    section: str | None = None
    snippet: str


class Answer(BaseModel):
    answer: str
    sources: list[Source]
    confidence: int = Field(ge=0, le=100)
    warnings: list[str] = []


class ExtractedEntity(BaseModel):
    kind: str  # date | amount | person | address | contract_number
    value: str
    normalized: str | None = None


class ExtractedPayment(BaseModel):
    amount: float
    currency: str = "RUB"
    due_date: date | None = None
    description: str | None = None
