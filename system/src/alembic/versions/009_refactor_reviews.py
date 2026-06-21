"""009_refactor_reviews

Revision ID: 009
Revises: 008
Create Date: 2026-05-16

Changes:
- Drop persona_id column from reviews
- Change rating column from SmallInt to Numeric(3,1) to support half-star values (e.g. 4.5)
- Update CHECK constraint accordingly
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "c4d5e6f7a8b9"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Drop the old CHECK constraint on rating (if exists)
    conn.execute(sa.text(
        "ALTER TABLE reviews DROP CONSTRAINT IF EXISTS ck_reviews_rating"
    ))

    # 2. Drop the index on persona_id (if exists)
    conn.execute(sa.text(
        "DROP INDEX IF EXISTS ix_reviews_persona_id"
    ))

    # 3. Drop the persona_id FK constraint (if exists) then the column (if exists)
    conn.execute(sa.text(
        "ALTER TABLE reviews DROP CONSTRAINT IF EXISTS reviews_persona_id_fkey"
    ))
    conn.execute(sa.text(
        "ALTER TABLE reviews DROP COLUMN IF EXISTS persona_id"
    ))

    # 4. Change rating from SmallInteger to Numeric(3,1)
    op.alter_column(
        "reviews",
        "rating",
        type_=sa.Numeric(3, 1),
        existing_type=sa.SmallInteger(),
        postgresql_using="rating::numeric(3,1)",
        nullable=False,
        server_default=sa.text("5.0"),
    )

    # 5. Add new CHECK constraint for float rating range
    conn.execute(sa.text(
        "ALTER TABLE reviews DROP CONSTRAINT IF EXISTS ck_reviews_rating"
    ))
    op.create_check_constraint(
        "ck_reviews_rating",
        "reviews",
        "rating >= 0.5 AND rating <= 5.0",
    )


def downgrade() -> None:
    # 1. Drop new CHECK constraint
    op.drop_constraint("ck_reviews_rating", "reviews", type_="check")

    # 2. Revert rating back to SmallInteger (truncates decimals)
    op.alter_column(
        "reviews",
        "rating",
        type_=sa.SmallInteger(),
        existing_type=sa.Numeric(3, 1),
        postgresql_using="rating::smallint",
        nullable=False,
        server_default=sa.text("5"),
    )

    # 3. Restore old CHECK constraint
    op.create_check_constraint(
        "ck_reviews_rating",
        "reviews",
        "rating >= 1 AND rating <= 5",
    )

    # 4. Re-add persona_id column
    op.add_column(
        "reviews",
        sa.Column(
            "persona_id",
            sa.BigInteger(),
            sa.ForeignKey("personas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # 5. Restore index
    op.create_index("ix_reviews_persona_id", "reviews", ["persona_id"])
