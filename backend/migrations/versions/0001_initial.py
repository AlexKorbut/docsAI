"""Initial schema: vector extension + all tables.

Revision ID: 0001
Revises:
Create Date: 2026-07-12
"""

from alembic import op

from app.storage.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.execute(
        "CREATE INDEX IF NOT EXISTS chunks_text_fts "
        "ON chunks USING gin (to_tsvector('russian', text))"
    )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
