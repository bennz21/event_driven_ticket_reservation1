from typing import Optional
from app.models import Booking, Event
from app.schemas import BookingResponse, EventResponse, PaymentResponse, TicketResponse


def serialize_event(event: Event, organizer_name: Optional[str] = None) -> EventResponse:
    resolved_name = organizer_name
    if resolved_name is None and event.organizer is not None:
        resolved_name = event.organizer.name
    return EventResponse(
        id=event.id,
        organizer_id=event.organizer_id,
        organizer_name=resolved_name,
        title=event.title,
        description=event.description,
        event_date=event.event_date,
        event_time=event.event_time,
        venue=event.venue,
        ticket_price=float(event.ticket_price),
        seating_type=event.seating_type.value,
        total_rows=event.total_rows,
        seats_per_row=event.seats_per_row,
        total_tickets=event.total_tickets,
        available_tickets=event.available_tickets,
        approval_status=event.approval_status.value,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def serialize_booking(booking: Booking) -> BookingResponse:
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        user_name=booking.user.name if booking.user else None,
        user_email=booking.user.email if booking.user else None,
        event_id=booking.event_id,
        event_title=booking.event.title if booking.event else None,
        event_date=booking.event.event_date if booking.event else None,
        event_time=booking.event.event_time if booking.event else None,
        venue=booking.event.venue if booking.event else None,
        ticket_count=booking.ticket_count,
        total_amount=float(booking.total_amount),
        status=booking.status.value,
        booked_at=booking.booked_at,
        payment=(
            PaymentResponse(
                id=booking.payment.id,
                booking_id=booking.payment.booking_id,
                amount=float(booking.payment.amount),
                status=booking.payment.status.value,
                gateway_transaction_id=booking.payment.gateway_transaction_id,
                paid_at=booking.payment.paid_at,
            )
            if booking.payment
            else None
        ),
        tickets=[TicketResponse.model_validate(t) for t in booking.tickets],
    )
