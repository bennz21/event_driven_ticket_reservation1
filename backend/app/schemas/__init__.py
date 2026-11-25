import datetime
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator
from app.models import SeatStatus, ReservationStatus

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- Auth & User Schemas ---
class UserRegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not _EMAIL_RE.match(cleaned):
            raise ValueError("Please provide a valid email address.")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class UserLoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: int
    email: Optional[str] = None
    full_name: str
    auth_provider: str
    avatar_url: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class OAuthExchangeRequest(BaseModel):
    code: str


class OAuthDemoRequest(BaseModel):
    provider: Literal["google", "apple"]
    email: Optional[str] = None
    full_name: Optional[str] = None


class OAuthProviderStatus(BaseModel):
    configured: bool
    demo_enabled: bool


class AuthProvidersResponse(BaseModel):
    google: OAuthProviderStatus
    apple: OAuthProviderStatus

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
    user_id: Optional[int] = None
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
