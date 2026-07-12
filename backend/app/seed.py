"""Seed the database with the sample document via the real ingestion pipeline.

Usage: python -m app.seed   (requires DB + API keys configured)
"""

import asyncio
import io
from pathlib import Path

from fastapi import UploadFile

from app.api.routes.documents import upload_document
from app.storage.db import get_session_factory

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


async def seed() -> None:
    session = get_session_factory()()
    try:
        for path in sorted(SAMPLES_DIR.glob("*")):
            if path.suffix.lower() not in {".md", ".txt", ".pdf"}:
                continue
            upload = UploadFile(filename=path.name, file=io.BytesIO(path.read_bytes()))
            result = await upload_document(upload, family_member=None, db=session)
            print(f"Ingested {path.name}: {result.model_dump()}")
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(seed())
