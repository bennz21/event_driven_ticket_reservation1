"""Create users, events, bookings, payments, and tickets InnoDB tables.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-26 14:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("organizer", "public", name="user_role_enum"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "blocked", name="user_status_enum"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("organizer_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_time", sa.Time(), nullable=False),
        sa.Column("venue", sa.String(length=200), nullable=False),
        sa.Column("ticket_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total_tickets", sa.Integer(), nullable=False),
        sa.Column("available_tickets", sa.Integer(), nullable=False),
        sa.Column(
            "approval_status",
            sa.Enum("pending", "approved", "rejected", name="approval_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_events_id", "events", ["id"])
    op.create_index("ix_events_organizer_id", "events", ["organizer_id"])
    op.create_index("ix_events_title", "events", ["title"])
    op.create_index("ix_events_event_date", "events", ["event_date"])
    op.create_index("ix_events_venue", "events", ["venue"])
    op.create_index("ix_events_approval_status", "events", ["approval_status"])
    op.create_index("ix_events_approval_date", "events", ["approval_status", "event_date"])

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("ticket_count", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "confirmed", "cancelled", "failed", name="booking_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("booked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_bookings_id", "bookings", ["id"])
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])
    op.create_index("ix_bookings_event_id", "bookings", ["event_id"])
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.create_index("ix_bookings_booked_at", "bookings", ["booked_at"])
    op.create_index("ix_bookings_user_status", "bookings", ["user_id", "status"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "success", "failed", "refunded", name="payment_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("gateway_transaction_id", sa.String(length=120), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_payments_id", "payments", ["id"])
    op.create_index("ix_payments_booking_id", "payments", ["booking_id"], unique=True)
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_gateway_transaction_id", "payments", ["gateway_transaction_id"])

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("ticket_code", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_tickets_id", "tickets", ["id"])
    op.create_index("ix_tickets_booking_id", "tickets", ["booking_id"])
    op.create_index("ix_tickets_event_id", "tickets", ["event_id"])
    op.create_index("ix_tickets_ticket_code", "tickets", ["ticket_code"], unique=True)


def downgrade() -> None:
    op.drop_table("tickets")
    op.drop_table("payments")
    op.drop_table("bookings")
    op.drop_table("events")
    op.drop_table("users")
