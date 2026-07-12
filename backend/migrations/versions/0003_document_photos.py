"""Photo-first ingestion: document_files table (multiple originals per document).

Backfills existing single-file documents. Idempotent, same as 0002.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-12
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_files (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            position INTEGER NOT NULL DEFAULT 0,
            filename VARCHAR(500) NOT NULL,
            stored_path VARCHAR(1000) NOT NULL,
            mime_type VARCHAR(200),
            size_bytes INTEGER
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS document_files_document_id "
        "ON document_files (document_id)"
    )
    # Backfill legacy single-file documents (skip already-migrated ones).
    op.execute(
        """
        INSERT INTO document_files (document_id, position, filename, stored_path,
                                    mime_type, size_bytes)
        SELECT d.id, 0, COALESCE(d.source_filename, 'document'), d.stored_path,
               d.mime_type, d.size_bytes
        FROM documents d
        WHERE d.stored_path IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM document_files f WHERE f.document_id = d.id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_files")
