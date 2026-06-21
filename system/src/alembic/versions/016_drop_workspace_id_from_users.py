"""016_drop_workspace_id_from_users

Revision ID: 016
Revises: 015
Create Date: 2026-05-16

Changes:
- Drop workspace_id column (FK→workspaces.id CASCADE, nullable) from users table
- Drop index ix_users_workspace_id
- Drop composite unique constraint uq_users_email_workspace
- Add global unique constraint uq_users_email (email globally unique)
- Workspace association for app users is via user_personas → workspace_personas
"""

import sqlalchemy as sa
from alembic import op

revision = "d1e2f3a4b5c7"
down_revision = "c0d1e2f3a4b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email_workspace"))
    conn.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_workspace_id_fkey"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_users_workspace_id"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS workspace_id"))
    conn.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email"))
    op.create_unique_constraint("uq_users_email", "users", ["email"])

def downgrade() -> None:
    # 1. Drop global unique constraint
    op.drop_constraint("uq_users_email", "users", type_="unique")

    # 2. Re-add workspace_id column (nullable)
    op.add_column("users", sa.Column("workspace_id", sa.BigInteger(), nullable=True))

    # 3. Re-add FK + index
    op.create_foreign_key(
        "users_workspace_id_fkey",
        "users", "workspaces",
        ["workspace_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"])

    # 4. Restore composite unique constraint
    op.create_unique_constraint(
        "uq_users_email_workspace", "users", ["email", "workspace_id"]
    )
