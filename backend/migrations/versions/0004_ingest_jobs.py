"""Background ingestion jobs.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-12
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ingest_jobs (
            id VARCHAR(32) PRIMARY KEY,
            kind VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            family_member VARCHAR(200),
            files JSONB NOT NULL,
            progress_done INTEGER NOT NULL DEFAULT 0,
            progress_total INTEGER NOT NULL DEFAULT 0,
            result JSONB,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ingest_jobs_status ON ingest_jobs (status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ingest_jobs")
