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


class DocumentInfo(BaseModel):
    id: int
    title: str
    category: str
    created_at: datetime


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
