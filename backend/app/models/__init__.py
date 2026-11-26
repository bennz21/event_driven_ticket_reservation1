import datetime
import enum
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserRole(str, enum.Enum):
    ORGANIZER = "organizer"
    PUBLIC = "public"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SeatingType(str, enum.Enum):
    SEATED = "seated"
    OPEN = "open"


class SeatStatus(str, enum.Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    BOOKED = "booked"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class User(Base):
    __tablename__ = "users"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
    }

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        SQLEnum(UserRole, values_callable=_enum_values, name="user_role_enum"),
        nullable=False,
        index=True,
    )
    status = Column(
        SQLEnum(UserStatus, values_callable=_enum_values, name="user_status_enum"),
        nullable=False,
        default=UserStatus.ACTIVE,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    events = relationship("Event", back_populates="organizer", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_approval_date", "approval_status", "event_date"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
        },
    )

    id = Column(Integer, primary_key=True, index=True)
    organizer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(Time, nullable=False)
    venue = Column(String(200), nullable=False, index=True)
    ticket_price = Column(Numeric(10, 2), nullable=False)
    seating_type = Column(
        SQLEnum(SeatingType, values_callable=_enum_values, name="seating_type_enum"),
        nullable=False,
        default=SeatingType.OPEN,
        index=True,
    )
    total_rows = Column(Integer, nullable=True)
    seats_per_row = Column(Integer, nullable=True)
    total_tickets = Column(Integer, nullable=False)
    available_tickets = Column(Integer, nullable=False)
    approval_status = Column(
        SQLEnum(ApprovalStatus, values_callable=_enum_values, name="approval_status_enum"),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    organizer = relationship("User", back_populates="events")
    seats = relationship("Seat", back_populates="event", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="event", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="event", cascade="all, delete-orphan")


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        Index("uq_seat_event_row_num", "event_id", "row_label", "seat_number", unique=True),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
        },
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_label = Column(String(10), nullable=False)
    seat_number = Column(Integer, nullable=False)
    status = Column(
        SQLEnum(SeatStatus, values_callable=_enum_values, name="seat_status_enum"),
        nullable=False,
        default=SeatStatus.AVAILABLE,
        index=True,
    )
    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event = relationship("Event", back_populates="seats")
    booking = relationship("Booking", back_populates="seats")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_user_status", "user_id", "status"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
        },
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_count = Column(Integer, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        SQLEnum(BookingStatus, values_callable=_enum_values, name="booking_status_enum"),
        nullable=False,
        default=BookingStatus.PENDING,
        index=True,
    )
    booked_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")
    seats = relationship("Seat", back_populates="booking")
    payment = relationship("Payment", back_populates="booking", uselist=False, cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="booking", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
    }

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        SQLEnum(PaymentStatus, values_callable=_enum_values, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )
    gateway_transaction_id = Column(String(120), nullable=True, index=True)
    paid_at = Column(DateTime, nullable=True)

    booking = relationship("Booking", back_populates="payment")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
    }

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seat_id = Column(
        Integer,
        ForeignKey("seats.id", ondelete="SET NULL"),
        nullable=True,
    )
    seat_label = Column(String(20), nullable=True)
    ticket_code = Column(String(64), unique=True, nullable=False, index=True)

    booking = relationship("Booking", back_populates="tickets")
    event = relationship("Event", back_populates="tickets")
