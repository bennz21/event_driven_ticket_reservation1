import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models import SeatStatus, ReservationStatus

# --- Event Schemas ---
class EventBase(BaseModel):
    title: str
    description: Optional[str] = ""
    venue_name: str
    event_date: datetime.datetime
    total_rows: int = 6
    seats_per_row: int = 10
    base_price: float = 50.0

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Seat Schemas ---
class SeatResponse(BaseModel):
    id: int
    event_id: int
    row: str
    seat_number: int
    tier: str
    price: float
    status: SeatStatus
    held_by_session_id: Optional[str] = None
    held_until: Optional[datetime.datetime] = None
    version: int

    class Config:
        from_attributes = True

class SeatHoldRequest(BaseModel):
    seat_ids: List[int]
    session_id: str

class SeatReleaseRequest(BaseModel):
    seat_ids: List[int]
    session_id: str

class SeatHoldResult(BaseModel):
    success: bool
    held_seat_ids: List[int]
    failed_seat_ids: List[int]
    held_until: Optional[datetime.datetime] = None
    message: str

# --- Reservation & Ticket Schemas ---
class ReservationCreate(BaseModel):
    seat_ids: List[int]
    session_id: str
    customer_name: str
    customer_email: Optional[str] = ""

class TicketResponse(BaseModel):
    id: int
    seat_id: int
    ticket_code: str
    issued_at: datetime.datetime

    class Config:
        from_attributes = True

class ReservationResponse(BaseModel):
    id: int
    event_id: int
    customer_name: str
    customer_email: Optional[str] = ""
    total_amount: float
    status: ReservationStatus
    created_at: datetime.datetime
    tickets: List[TicketResponse]

    class Config:
        from_attributes = True

# --- WebSocket Message ---
class WSBroadcastMessage(BaseModel):
    type: str  # e.g., "SEAT_UPDATE", "HOLD_EXPIRED", "NEW_RESERVATION"
    event_id: int
    data: dict
    timestamp: float
