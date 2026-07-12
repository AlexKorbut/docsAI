from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings

EMBEDDING_DIM = get_settings().embedding_dim


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    # loan | utilities | medical | property | other
    category: Mapped[str] = mapped_column(String(50), index=True)
    family_member: Mapped[str | None] = mapped_column(String(200))
    source_filename: Mapped[str | None] = mapped_column(String(500))
    # Original uploaded file, kept verbatim on disk for viewing/downloading.
    stored_path: Mapped[str | None] = mapped_column(String(1000))
    mime_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int | None]
    raw_markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")
    entities: Mapped[list["Entity"]] = relationship(back_populates="document")
    payments: Mapped[list["Payment"]] = relationship(back_populates="document")
    files: Mapped[list["DocumentFile"]] = relationship(
        back_populates="document", order_by="DocumentFile.position"
    )


class DocumentFile(Base):
    """Original uploaded files: photo pages of a paper document, or one e-file."""

    __tablename__ = "document_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    position: Mapped[int] = mapped_column(default=0)  # page order for photos
    filename: Mapped[str] = mapped_column(String(500))
    stored_path: Mapped[str] = mapped_column(String(1000))
    mime_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int | None]

    document: Mapped[Document] = relationship(back_populates="files")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    page: Mapped[int | None]
    section: Mapped[str | None] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    document: Mapped[Document] = relationship(back_populates="chunks")


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    value: Mapped[str] = mapped_column(String(1000))
    normalized: Mapped[str | None] = mapped_column(String(1000))

    document: Mapped[Document] = relationship(back_populates="entities")


class Payment(Base):
    """Exact figures for structured queries — amounts/dates never go through the LLM."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    description: Mapped[str | None] = mapped_column(String(1000))

    document: Mapped[Document] = relationship(back_populates="payments")


class FamilyMember(Base):
    """Registry of family members documents can be attached to."""

    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    relation: Mapped[str | None] = mapped_column(String(100))  # мама, сын, ...
    birth_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class IngestJob(Base):
    """Background ingestion job: uploads return immediately, recognition runs async."""

    __tablename__ = "ingest_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid hex
    kind: Mapped[str] = mapped_column(String(20))  # single | batch
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    family_member: Mapped[str | None] = mapped_column(String(200))
    # [{filename, stored_path, content_type, size_bytes}] — originals already on disk
    files: Mapped[list] = mapped_column(JSONB)
    progress_done: Mapped[int] = mapped_column(default=0)
    progress_total: Mapped[int] = mapped_column(default=0)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AgentRun(Base):
    """Audit trail: one row per agent step of every query."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[str] = mapped_column(String(64), index=True)
    agent: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
