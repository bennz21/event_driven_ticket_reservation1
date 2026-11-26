from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentActor, require_organizer
from app.core.database import get_db
from app.models import ApprovalStatus, Booking, Event, Seat, SeatStatus, SeatingType
from app.routers.serializers import serialize_booking, serialize_event
from app.schemas import (
    BookingResponse,
    EventCreateRequest,
    EventResponse,
    EventUpdateRequest,
)
from app.services.pinecone_service import compute_event_hash, delete_event_vectors

router = APIRouter(dependencies=[Depends(require_organizer)])


def _generate_seats_for_event(
    db: Session,
    event_id: int,
    total_rows: int,
    seats_per_row: int,
) -> None:
    seats = []
    for row_idx in range(total_rows):
        row_label = chr(65 + row_idx)
        for seat_num in range(1, seats_per_row + 1):
            seats.append(
                Seat(
                    event_id=event_id,
                    row_label=row_label,
                    seat_number=seat_num,
                    status=SeatStatus.AVAILABLE,
                )
            )
    db.add_all(seats)


@router.get("/events", response_model=List[EventResponse])
def list_my_events(
    actor: CurrentActor = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    events = (
        db.execute(
            select(Event)
            .where(Event.organizer_id == actor.id)
            .order_by(Event.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [serialize_event(e, actor.name) for e in events]


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    req: EventCreateRequest,
    actor: CurrentActor = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    event = Event(
        organizer_id=actor.id,
        title=req.title.strip(),
        description=req.description.strip(),
        event_date=req.event_date,
        event_time=req.event_time,
        venue=req.venue.strip(),
        ticket_price=req.ticket_price,
        seating_type=SeatingType(req.seating_type),
        total_rows=req.total_rows,
        seats_per_row=req.seats_per_row,
        total_tickets=req.total_tickets,
        available_tickets=req.total_tickets,
        approval_status=ApprovalStatus.PENDING,
    )
    db.add(event)
    db.flush()

    if req.seating_type == "seated" and req.total_rows and req.seats_per_row:
        _generate_seats_for_event(db, event.id, req.total_rows, req.seats_per_row)

    db.commit()
    db.refresh(event)
    return serialize_event(event, actor.name)


@router.put("/events/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    req: EventUpdateRequest,
    actor: CurrentActor = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    event = db.execute(
        select(Event).where(Event.id == event_id).with_for_update()
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    if event.organizer_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own events.",
        )

    tickets_allocated = event.total_tickets - event.available_tickets
    new_seating_type = SeatingType(req.seating_type)

    if tickets_allocated > 0 and (
        new_seating_type != event.seating_type
        or (
            new_seating_type == SeatingType.SEATED
            and (req.total_rows != event.total_rows or req.seats_per_row != event.seats_per_row)
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change seating type or seat grid dimensions after tickets have been booked.",
        )

    if req.total_tickets < tickets_allocated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"total_tickets cannot be less than already booked/held tickets ({tickets_allocated}).",
        )

    layout_changed = (
        new_seating_type != event.seating_type
        or req.total_rows != event.total_rows
        or req.seats_per_row != event.seats_per_row
    )

    old_hash = event.embedding_hash
    event.title = req.title.strip()
    event.description = req.description.strip()
    event.event_date = req.event_date
    event.event_time = req.event_time
    event.venue = req.venue.strip()
    event.ticket_price = req.ticket_price
    event.seating_type = new_seating_type
    event.total_rows = req.total_rows
    event.seats_per_row = req.seats_per_row
    event.total_tickets = req.total_tickets
    event.available_tickets = req.total_tickets - tickets_allocated
    event.approval_status = ApprovalStatus.PENDING

    searchable_changed = old_hash is not None and compute_event_hash(event) != old_hash
    if searchable_changed:
        event.embedding_hash = None

    if layout_changed:
        db.execute(delete(Seat).where(Seat.event_id == event.id))
        if new_seating_type == SeatingType.SEATED and req.total_rows and req.seats_per_row:
            _generate_seats_for_event(db, event.id, req.total_rows, req.seats_per_row)

    db.commit()
    db.refresh(event)
    if searchable_changed:
        delete_event_vectors([event.id])
    return serialize_event(event, actor.name)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    actor: CurrentActor = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    event = db.execute(select(Event).where(Event.id == event_id)).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    if event.organizer_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own events.",
        )

    had_vector = bool(event.embedding_hash)
    db.delete(event)
    db.commit()
    if had_vector:
        delete_event_vectors([event_id])


@router.get("/bookings", response_model=List[BookingResponse])
def list_bookings_for_my_events(
    actor: CurrentActor = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    query = (
        select(Booking)
        .join(Event, Booking.event_id == Event.id)
        .where(Event.organizer_id == actor.id)
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
