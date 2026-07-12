"""Seed the database with sample documents via the real ingestion pipeline
(synchronously, bypassing the job queue).

Usage: python -m app.seed   (requires DB + API keys configured)
"""

from pathlib import Path

from app.ingestion.ingest import ingest_document
from app.ingestion.pipeline import StoredUpload, UploadItem, to_markdown
from app.llm.anthropic_client import get_llm
from app.storage import files
from app.storage.db import get_session_factory

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


def seed() -> None:
    session = get_session_factory()()
    llm = get_llm()
    try:
        for path in sorted(SAMPLES_DIR.glob("*")):
            if path.suffix.lower() not in {".md", ".txt", ".pdf", ".jpg", ".jpeg", ".png"}:
                continue
            content = path.read_bytes()
            item = UploadItem(filename=path.name, content=content)
            markdown, warnings = to_markdown([item], llm)
            stored = StoredUpload(
                filename=path.name,
                stored_path=files.save_upload(path.name, content),
                size_bytes=len(content),
            )
            result = ingest_document(markdown, [stored], None, warnings, llm, session)
            print(f"Ingested {path.name}: {result.model_dump()}")
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed()
