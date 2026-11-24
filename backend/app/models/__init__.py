import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class SeatStatus(str, enum.Enum):
    AVAILABLE = "available"
    HELD = "held"           # Temporarily locked while user is in checkout
    RESERVED = "reserved"   # Fully purchased & ticketed

class ReservationStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), default="")
    venue_name = Column(String(200), nullable=False)
    event_date = Column(DateTime, nullable=False)
    total_rows = Column(Integer, default=6)
    seats_per_row = Column(Integer, default=10)
    base_price = Column(Float, default=50.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    seats = relationship("Seat", back_populates="event", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="event")

class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    row = Column(String(10), nullable=False)           # e.g., 'A', 'B', 'VIP'
    seat_number = Column(Integer, nullable=False)      # e.g., 1, 2, 3
    tier = Column(String(50), default="standard")      # standard, premium, vip
    price = Column(Float, nullable=False)
    
    # State tracking
    status = Column(SQLEnum(SeatStatus), default=SeatStatus.AVAILABLE, nullable=False, index=True)
    held_by_session_id = Column(String(100), nullable=True, index=True)
    held_until = Column(DateTime, nullable=True, index=True)
    version = Column(Integer, default=1, nullable=False) # For optimistic locking

    # Relationships
    event = relationship("Event", back_populates="seats")
    tickets = relationship("Ticket", back_populates="seat")

    __table_args__ = (
        Index("ix_seat_event_row_num", "event_id", "row", "seat_number", unique=True),
    )

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    session_id = Column(String(100), nullable=False, index=True)
    customer_name = Column(String(150), nullable=False)
    customer_email = Column(String(150), nullable=True, default="")
    total_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(ReservationStatus), default=ReservationStatus.CONFIRMED, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="reservations")
    tickets = relationship("Ticket", back_populates="reservation", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    ticket_code = Column(String(64), unique=True, nullable=False, index=True)
    issued_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    reservation = relationship("Reservation", back_populates="tickets")
    seat = relationship("Seat", back_populates="tickets")
