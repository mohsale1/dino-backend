"""018_reviews_unique_user_workspace

Revision ID: 018
Revises: 017
Create Date: 2026-05-19

Changes:
- Add UniqueConstraint on (workspace_id, user_id) in reviews table
  to enforce one review per authenticated user per workspace.
- Partial: only applies when user_id IS NOT NULL (anonymous reviews
  are allowed to coexist freely).
- Deletes duplicate reviews keeping the most recent one before adding
  the constraint.
"""

import sqlalchemy as sa
from alembic import op

revision = "f3a4b5c6d7e9"
down_revision = "e2f3a4b5c6d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Remove duplicate (workspace_id, user_id) rows — keep the latest per pair
    op.execute(
        """
        DELETE FROM reviews
        WHERE id NOT IN (
            SELECT DISTINCT ON (workspace_id, user_id) id
            FROM reviews
            WHERE user_id IS NOT NULL
            ORDER BY workspace_id, user_id, created_at DESC
        )
        AND user_id IS NOT NULL
        """
    )

    # 2. Add partial unique index — only enforced when user_id IS NOT NULL
    op.create_index(
        "uq_reviews_workspace_user",
        "reviews",
        ["workspace_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_reviews_workspace_user", table_name="reviews")
