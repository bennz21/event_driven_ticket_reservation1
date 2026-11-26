"""Add embedding_hash column to events table for incremental Pinecone syncing.

Revision ID: 0003_event_embedding_hash
Revises: 0002_event_seating_and_seats
Create Date: 2026-11-26 16:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_event_embedding_hash"
down_revision: Union[str, None] = "0002_event_seating_and_seats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("embedding_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "embedding_hash")
