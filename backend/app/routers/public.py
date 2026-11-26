import datetime
import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentActor, require_public
from app.core.config import settings
from app.core.database import get_db
from app.models import (
    ApprovalStatus,
    Booking,
    BookingStatus,
    Event,
    Payment,
    PaymentStatus,
    Seat,
    SeatStatus,
    SeatingType,
    Ticket,
)
from app.routers.serializers import serialize_booking, serialize_event
from app.schemas import (
    BookingCreateRequest,
    BookingResponse,
    EventResponse,
    PaymentCheckoutRequest,
    SeatResponse,
)
from app.services.pinecone_service import (
    fetch_ordered_events_by_ids,
    get_similar_event_ids,
    search_event_ids,
)

router = APIRouter()


def _event_start_dt(event: Event) -> datetime.datetime:
    return datetime.datetime.combine(event.event_date, event.event_time)


def _fetch_full_booking(db: Session, booking_id: int) -> Booking:
    return (
        db.execute(
            select(Booking)
            .options(
                joinedload(Booking.user),
                joinedload(Booking.event),
                joinedload(Booking.payment),
                joinedload(Booking.tickets),
            )
            .where(Booking.id == booking_id)
        )
        .unique()
        .scalar_one()
    )


@router.get("/events", response_model=List[EventResponse])
def browse_approved_events(
    q: Optional[str] = Query(default=None, description="Search title, description, or venue"),
    city: Optional[str] = Query(default=None, description="Filter by venue/city"),
    max_price: Optional[float] = Query(default=None, gt=0, description="Maximum ticket price"),
    seating_type: Optional[str] = Query(default=None, description="Filter by seated or open"),
    db: Session = Depends(get_db),
):
    """Browse and search Admin-approved events (MySQL primary + semantic Pinecone fallback)."""
    query = (
        select(Event)
        .options(joinedload(Event.organizer))
        .where(Event.approval_status == ApprovalStatus.APPROVED)
        .order_by(Event.event_date.asc(), Event.event_time.asc())
    )
    if city and city.strip():
        query = query.where(Event.venue.ilike(f"%{city.strip()}%"))
    if max_price is not None:
        query = query.where(Event.ticket_price <= Decimal(str(max_price)))
    if seating_type in ("seated", "open"):
        query = query.where(Event.seating_type == SeatingType(seating_type))

    clean_q = q.strip() if q else ""
    if clean_q:
        pattern = f"%{clean_q}%"
        query = query.where(
            or_(
                Event.title.ilike(pattern),
                Event.description.ilike(pattern),
                Event.venue.ilike(pattern),
            )
        )
    events = db.execute(query).scalars().all()

    # Semantic fallback only when SQL returns empty and input is meaningful (>= 3 chars)
    if not events and len(clean_q) >= 3:
        matched_ids = search_event_ids(
            clean_q,
            top_k=5,
            city=city,
            seating_type=seating_type,
            max_price=max_price,
        )
        if matched_ids:
            events = fetch_ordered_events_by_ids(db, matched_ids)
            if city and city.strip():
                city_l = city.strip().lower()
                events = [e for e in events if city_l in (e.venue or "").lower()]
            if max_price is not None:
                events = [e for e in events if float(e.ticket_price) <= max_price]
            if seating_type in ("seated", "open"):
                events = [e for e in events if e.seating_type.value == seating_type]

    return [serialize_event(e) for e in events]


@router.get("/events/{event_id}", response_model=EventResponse)
def get_approved_event(event_id: int, db: Session = Depends(get_db)):
    event = db.execute(
        select(Event)
        .options(joinedload(Event.organizer))
        .where(
            Event.id == event_id,
            Event.approval_status == ApprovalStatus.APPROVED,
        )
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approved event not found.",
        )
    return serialize_event(event)


@router.get("/events/{event_id}/similar", response_model=List[EventResponse])
def get_similar_events(
    event_id: int,
    limit: int = Query(default=4, ge=1, le=5),
    db: Session = Depends(get_db),
):
    """Return similar upcoming approved events (TTL-cached Pinecone lookup with MySQL fallback)."""
    event = db.execute(
        select(Event).where(
            Event.id == event_id,
            Event.approval_status == ApprovalStatus.APPROVED,
        )
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approved event not found.",
        )

    similar_ids = get_similar_event_ids(event, top_k=limit)
    similar = fetch_ordered_events_by_ids(db, similar_ids)
    if not similar:
        today = datetime.date.today()
        similar = (
            db.execute(
                select(Event)
                .options(joinedload(Event.organizer))
                .where(
                    Event.id != event.id,
                    Event.approval_status == ApprovalStatus.APPROVED,
                    Event.event_date >= today,
                )
                .order_by(Event.event_date.asc(), Event.event_time.asc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    return [serialize_event(e) for e in similar]


@router.get("/events/{event_id}/seats", response_model=List[SeatResponse])
def get_event_seats(event_id: int, db: Session = Depends(get_db)):
    """Return live seat availability for an approved seated event."""
    event = db.execute(
        select(Event).where(
            Event.id == event_id,
            Event.approval_status == ApprovalStatus.APPROVED,
        )
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approved event not found.",
        )
    if event.seating_type != SeatingType.SEATED:
        return []

    seats = (
        db.execute(
            select(Seat)
            .where(Seat.event_id == event_id)
            .order_by(Seat.row_label.asc(), Seat.seat_number.asc())
        )
        .scalars()
        .all()
    )
    return seats


@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    req: BookingCreateRequest,
    actor: CurrentActor = Depends(require_public),
    db: Session = Depends(get_db),
):
    """
    Create a pending booking inside a DB transaction using SELECT ... FOR UPDATE
    on the Event (and Seat rows for seated events) so concurrent users cannot double-book.
    """
    try:
        event = db.execute(
            select(Event)
            .where(Event.id == req.event_id)
            .with_for_update()
        ).scalar_one_or_none()

        if event is None or event.approval_status != ApprovalStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approved event not found.",
            )

        if _event_start_dt(event) <= datetime.datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book tickets for an event that has already started.",
            )

        selected_seats: List[Seat] = []
        if event.seating_type == SeatingType.SEATED:
            unique_seat_ids = list(dict.fromkeys(req.seat_ids or []))
            if not unique_seat_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please select at least one seat for this seated event.",
                )
            if len(unique_seat_ids) > settings.MAX_TICKETS_PER_BOOKING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum {settings.MAX_TICKETS_PER_BOOKING} seats allowed per booking.",
                )

            selected_seats = (
                db.execute(
                    select(Seat)
                    .where(
                        Seat.event_id == event.id,
                        Seat.id.in_(unique_seat_ids),
                    )
                    .order_by(Seat.id.asc())
                    .with_for_update()
                )
                .scalars()
                .all()
            )
            if len(selected_seats) != len(unique_seat_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more selected seats do not belong to this event.",
                )

            unavailable = [
                f"{s.row_label}{s.seat_number}"
                for s in selected_seats
                if s.status != SeatStatus.AVAILABLE
            ]
            if unavailable:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Seat(s) already taken or pending: {', '.join(unavailable)}",
                )

            count = len(selected_seats)
        else:
            count = req.ticket_count or 0
            if count < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ticket_count must be at least 1.",
                )
            if count > settings.MAX_TICKETS_PER_BOOKING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum {settings.MAX_TICKETS_PER_BOOKING} tickets allowed per booking.",
                )

        if event.available_tickets <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This event is sold out.",
            )

        if event.available_tickets < count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only {event.available_tickets} ticket(s) remaining.",
            )

        total_amount = Decimal(event.ticket_price) * count
        event.available_tickets -= count

        booking = Booking(
            user_id=actor.id,
            event_id=event.id,
            ticket_count=count,
            total_amount=total_amount,
            status=BookingStatus.PENDING,
        )
        db.add(booking)
        db.flush()

        for seat in selected_seats:
            seat.status = SeatStatus.PENDING
            seat.booking_id = booking.id

        payment = Payment(
            booking_id=booking.id,
            amount=total_amount,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return serialize_booking(_fetch_full_booking(db, booking.id))


@router.post("/bookings/{booking_id}/pay", response_model=BookingResponse)
def pay_for_booking(
    booking_id: int,
    req: PaymentCheckoutRequest,
    actor: CurrentActor = Depends(require_public),
    db: Session = Depends(get_db),
):
    """
    Process payment gateway transaction for a pending booking.
    On success: confirms booking, marks selected seats as booked, and issues tickets.
    On failure: releases held seats and restores event available_tickets.
    """
    try:
        booking = db.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .with_for_update()
        ).scalar_one_or_none()

        if booking is None or booking.user_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found.",
            )

        if booking.status != BookingStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Booking is already {booking.status.value}.",
            )

        event = db.execute(
            select(Event).where(Event.id == booking.event_id).with_for_update()
        ).scalar_one()
        payment = db.execute(
            select(Payment).where(Payment.booking_id == booking.id).with_for_update()
        ).scalar_one()
        held_seats = (
            db.execute(
                select(Seat)
                .where(Seat.booking_id == booking.id)
                .order_by(Seat.row_label.asc(), Seat.seat_number.asc())
                .with_for_update()
            )
            .scalars()
            .all()
        )

        now = datetime.datetime.utcnow()
        if req.simulate_outcome == "failed":
            payment.status = PaymentStatus.FAILED
            payment.gateway_transaction_id = f"GW-FAIL-{uuid.uuid4().hex[:10].upper()}"
            payment.paid_at = now
            booking.status = BookingStatus.FAILED
            event.available_tickets = min(
                event.total_tickets,
                event.available_tickets + booking.ticket_count,
            )
            for seat in held_seats:
                seat.status = SeatStatus.AVAILABLE
                seat.booking_id = None
            db.commit()
        else:
            payment.status = PaymentStatus.SUCCESS
            payment.gateway_transaction_id = (
                f"GW-{req.payment_method.upper()}-{uuid.uuid4().hex[:10].upper()}"
            )
            payment.paid_at = now
            booking.status = BookingStatus.CONFIRMED

            if held_seats:
                for seat in held_seats:
                    seat.status = SeatStatus.BOOKED
                    label = f"{seat.row_label}{seat.seat_number}"
                    db.add(
                        Ticket(
                            booking_id=booking.id,
                            event_id=event.id,
                            seat_id=seat.id,
                            seat_label=label,
                            ticket_code=f"TICK-{event.id}-{label}-{uuid.uuid4().hex[:6].upper()}",
                        )
                    )
            else:
                for _ in range(booking.ticket_count):
                    db.add(
                        Ticket(
                            booking_id=booking.id,
                            event_id=event.id,
                            ticket_code=f"TICK-{event.id}-{booking.id}-{uuid.uuid4().hex[:8].upper()}",
                        )
                    )
            db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return serialize_booking(_fetch_full_booking(db, booking.id))


@router.get("/bookings", response_model=List[BookingResponse])
def list_my_bookings(
    actor: CurrentActor = Depends(require_public),
    db: Session = Depends(get_db),
):
    query = (
        select(Booking)
        .where(Booking.user_id == actor.id)
        .options(
            joinedload(Booking.user),
            joinedload(Booking.event),
            joinedload(Booking.payment),
            joinedload(Booking.tickets),
        )
        .order_by(Booking.booked_at.desc())
    )
    bookings = db.execute(query).unique().scalars().all()
    return [serialize_booking(b) for b in bookings]


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_my_booking(
    booking_id: int,
    actor: CurrentActor = Depends(require_public),
    db: Session = Depends(get_db),
):
    booking = (
        db.execute(
            select(Booking)
            .where(Booking.id == booking_id, Booking.user_id == actor.id)
            .options(
                joinedload(Booking.user),
                joinedload(Booking.event),
                joinedload(Booking.payment),
                joinedload(Booking.tickets),
            )
        )
        .unique()
        .scalar_one_or_none()
    )
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    return serialize_booking(booking)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    actor: CurrentActor = Depends(require_public),
    db: Session = Depends(get_db),
):
    """Cancel a booking before the event starts and restore tickets/seats inside a transaction."""
    try:
        booking = db.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .with_for_update()
        ).scalar_one_or_none()

        if booking is None or booking.user_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found.",
            )

        if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel a booking with status '{booking.status.value}'.",
            )

        event = db.execute(
            select(Event).where(Event.id == booking.event_id).with_for_update()
        ).scalar_one()

        if _event_start_dt(event) <= datetime.datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a booking after the event has started.",
            )

        payment = db.execute(
            select(Payment).where(Payment.booking_id == booking.id).with_for_update()
        ).scalar_one_or_none()
        linked_seats = (
            db.execute(
                select(Seat).where(Seat.booking_id == booking.id).with_for_update()
            )
            .scalars()
            .all()
        )

        booking.status = BookingStatus.CANCELLED
        event.available_tickets = min(
            event.total_tickets,
            event.available_tickets + booking.ticket_count,
        )

        for seat in linked_seats:
            seat.status = SeatStatus.AVAILABLE
            seat.booking_id = None

        if payment is not None:
            if payment.status == PaymentStatus.SUCCESS:
                payment.status = PaymentStatus.REFUNDED
            elif payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.FAILED

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return serialize_booking(_fetch_full_booking(db, booking.id))
