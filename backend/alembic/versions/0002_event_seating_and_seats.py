"""Add event seating_type, seats table, and ticket seat metadata.

Revision ID: 0002_event_seating_and_seats
Revises: 0001_initial_schema
Create Date: 2026-11-26 15:35:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_event_seating_and_seats"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "seating_type",
            sa.Enum("seated", "open", name="seating_type_enum"),
            nullable=False,
            server_default="open",
        ),
    )
    op.add_column("events", sa.Column("total_rows", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("seats_per_row", sa.Integer(), nullable=True))
    op.create_index("ix_events_seating_type", "events", ["seating_type"])

    op.create_table(
        "seats",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("row_label", sa.String(length=10), nullable=False),
        sa.Column("seat_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("available", "pending", "booked", name="seat_status_enum"),
            nullable=False,
            server_default="available",
        ),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_seats_id", "seats", ["id"])
    op.create_index("ix_seats_event_id", "seats", ["event_id"])
    op.create_index("ix_seats_status", "seats", ["status"])
    op.create_index("ix_seats_booking_id", "seats", ["booking_id"])
    op.create_index(
        "uq_seat_event_row_num",
        "seats",
        ["event_id", "row_label", "seat_number"],
        unique=True,
    )

    op.add_column("tickets", sa.Column("seat_id", sa.Integer(), nullable=True))
    op.add_column("tickets", sa.Column("seat_label", sa.String(length=20), nullable=True))
    op.create_foreign_key(
        "fk_tickets_seat",
        "tickets",
        "seats",
        ["seat_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tickets_seat", "tickets", type_="foreignkey")
    op.drop_column("tickets", "seat_label")
    op.drop_column("tickets", "seat_id")

    op.drop_table("seats")

    op.drop_index("ix_events_seating_type", table_name="events")
    op.drop_column("events", "seats_per_row")
    op.drop_column("events", "total_rows")
    op.drop_column("events", "seating_type")
