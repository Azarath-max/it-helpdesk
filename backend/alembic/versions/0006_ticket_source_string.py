"""Change ticket source from an enum to a free-form external system label.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "tickets",
        "source",
        existing_type=sa.Enum("WEB", "WEBHOOK", name="ticket_source"),
        type_=sa.String(length=80),
        existing_nullable=False,
        postgresql_using="source::text",
    )
    op.alter_column(
        "tickets",
        "source",
        server_default=sa.text("'web'"),
    )
    op.execute("DROP TYPE IF EXISTS ticket_source")


def downgrade() -> None:
    op.execute("CREATE TYPE ticket_source AS ENUM ('WEB', 'WEBHOOK')")
    op.alter_column(
        "tickets",
        "source",
        existing_type=sa.String(length=80),
        type_=sa.Enum("WEB", "WEBHOOK", name="ticket_source"),
        existing_nullable=False,
        postgresql_using="source::ticket_source",
    )
