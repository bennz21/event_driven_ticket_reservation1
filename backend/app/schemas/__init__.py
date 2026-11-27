import datetime
import re
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

_BASIC_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- Auth Schemas ---
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["organizer", "public"]

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters.")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not _BASIC_EMAIL_RE.match(cleaned):
            raise ValueError("Please provide a valid email address.")
        return cleaned


class AuthIdentity(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    role: Literal["admin", "organizer", "public"]
    status: str = "active"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthIdentity


# --- Admin User Management Schemas ---
class UserAdminResponse(BaseModel):
    id: int
    name: str
    email: str
    role: Literal["organizer", "public"]
    status: Literal["active", "blocked"]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class UserStatusUpdate(BaseModel):
    status: Literal["active", "blocked"]


# --- Event & Seat Schemas ---
class EventUpsertRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5, max_length=5000)
    event_date: datetime.date
    event_time: datetime.time
    venue: str = Field(..., min_length=2, max_length=200)
    ticket_price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    seating_type: Literal["seated", "open"] = "open"
    total_rows: Optional[int] = Field(default=None, ge=1, le=26)
    seats_per_row: Optional[int] = Field(default=None, ge=1, le=30)
    total_tickets: Optional[int] = Field(default=None, ge=1, le=100000)

    @model_validator(mode="after")
    def validate_seating_config(self) -> "EventUpsertRequest":
        if self.seating_type == "seated":
            if self.total_rows is None or self.seats_per_row is None:
                raise ValueError(
                    "total_rows and seats_per_row are required for a limited seated event."
                )
            self.total_tickets = self.total_rows * self.seats_per_row
        else:
            if self.total_tickets is None:
                raise ValueError("total_tickets is required for an open event.")
            self.total_rows = None
            self.seats_per_row = None
        return self


EventCreateRequest = EventUpsertRequest
EventUpdateRequest = EventUpsertRequest


class SeatResponse(BaseModel):
    id: int
    event_id: int
    row_label: str
    seat_number: int
    status: Literal["available", "pending", "booked"]
    booking_id: Optional[int] = None

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    id: int
    organizer_id: int
    organizer_name: Optional[str] = None
    title: str
    description: str
    event_date: datetime.date
    event_time: datetime.time
    venue: str
    ticket_price: float
    seating_type: Literal["seated", "open"]
    total_rows: Optional[int] = None
    seats_per_row: Optional[int] = None
    total_tickets: int
    available_tickets: int
    approval_status: Literal["pending", "approved", "rejected"]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


# --- Booking, Payment & Ticket Schemas ---
class BookingCreateRequest(BaseModel):
    event_id: int
    ticket_count: Optional[int] = Field(default=None, ge=1, le=20)
    seat_ids: Optional[List[int]] = None


class PaymentCheckoutRequest(BaseModel):
    payment_method: Literal["card", "upi", "netbanking", "razorpay"] = "razorpay"
    card_last4: Optional[str] = Field(default="4242", max_length=4)
    simulate_outcome: Literal["success", "failed"] = "success"
    razorpay_payment_id: Optional[str] = Field(default=None, max_length=120)
    razorpay_order_id: Optional[str] = Field(default=None, max_length=120)
    razorpay_signature: Optional[str] = Field(default=None, max_length=256)


class RazorpayOrderResponse(BaseModel):
    enabled: bool
    mode: Literal["server_order", "client_checkout", "simulated"]
    key_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: int
    currency: str
    booking_id: int
    event_title: str
    prefill_name: str
    prefill_email: str


class TicketResponse(BaseModel):
    id: int
    booking_id: int
    event_id: int
    seat_id: Optional[int] = None
    seat_label: Optional[str] = None
    ticket_code: str

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: float
    status: Literal["pending", "success", "failed", "refunded"]
    gateway_transaction_id: Optional[str] = None
    paid_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    event_id: int
    event_title: Optional[str] = None
    event_date: Optional[datetime.date] = None
    event_time: Optional[datetime.time] = None
    venue: Optional[str] = None
    ticket_count: int
    total_amount: float
    status: Literal["pending", "confirmed", "cancelled", "failed"]
    booked_at: datetime.datetime
    payment: Optional[PaymentResponse] = None
    tickets: List[TicketResponse] = []

    class Config:
        from_attributes = True


class AdminPaymentDetailResponse(BaseModel):
    id: int
    booking_id: int
    amount: float
    status: Literal["pending", "success", "failed", "refunded"]
    gateway_transaction_id: Optional[str] = None
    paid_at: Optional[datetime.datetime] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    event_title: Optional[str] = None
    booking_status: str
