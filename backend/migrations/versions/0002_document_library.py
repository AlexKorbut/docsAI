"""Document library: original-file columns + family_members table.

Idempotent (IF NOT EXISTS) so it is safe both after an old 0001 run and after a
fresh 0001 run whose create_all already produced the new schema.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-12
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS stored_path VARCHAR(1000)")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type VARCHAR(200)")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS size_bytes INTEGER")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS family_members (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL UNIQUE,
            relation VARCHAR(100),
            birth_date DATE,
            notes TEXT
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS family_members")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS stored_path")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS mime_type")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS size_bytes")
