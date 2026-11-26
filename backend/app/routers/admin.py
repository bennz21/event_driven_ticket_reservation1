from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_admin
from app.core.database import get_db
from app.models import ApprovalStatus, Booking, Event, Payment, User, UserStatus
from app.routers.serializers import serialize_booking, serialize_event
from app.schemas import (
    AdminPaymentDetailResponse,
    BookingResponse,
    EventResponse,
    UserAdminResponse,
    UserStatusUpdate,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/events", response_model=List[EventResponse])
def list_all_events(
    approval_status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(Event).options(joinedload(Event.organizer)).order_by(Event.created_at.desc())
    if approval_status:
        try:
            status_enum = ApprovalStatus(approval_status)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid approval_status filter.",
            ) from exc
        query = query.where(Event.approval_status == status_enum)

    events = db.execute(query).scalars().all()
    return [serialize_event(e) for e in events]


@router.post("/events/{event_id}/approve", response_model=EventResponse)
def approve_event(event_id: int, db: Session = Depends(get_db)):
    event = db.execute(
        select(Event).options(joinedload(Event.organizer)).where(Event.id == event_id)
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    event.approval_status = ApprovalStatus.APPROVED
    db.commit()
    db.refresh(event)
    return serialize_event(event)


@router.post("/events/{event_id}/reject", response_model=EventResponse)
def reject_event(event_id: int, db: Session = Depends(get_db)):
    event = db.execute(
        select(Event).options(joinedload(Event.organizer)).where(Event.id == event_id)
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    event.approval_status = ApprovalStatus.REJECTED
    db.commit()
    db.refresh(event)
    return serialize_event(event)


@router.get("/users", response_model=List[UserAdminResponse])
def list_users(
    role: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(User).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    return db.execute(query).scalars().all()


@router.patch("/users/{user_id}/status", response_model=UserAdminResponse)
def update_user_status(
    user_id: int,
    req: UserStatusUpdate,
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.status = UserStatus(req.status)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    db.delete(user)
    db.commit()


@router.get("/bookings", response_model=List[BookingResponse])
def list_all_bookings(db: Session = Depends(get_db)):
    query = (
        select(Booking)
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


@router.get("/payments", response_model=List[AdminPaymentDetailResponse])
def list_all_payments(db: Session = Depends(get_db)):
    query = (
        select(Payment)
        .options(
            joinedload(Payment.booking).joinedload(Booking.user),
            joinedload(Payment.booking).joinedload(Booking.event),
        )
        .order_by(Payment.id.desc())
    )
    payments = db.execute(query).scalars().all()
    return [
        AdminPaymentDetailResponse(
            id=p.id,
            booking_id=p.booking_id,
            amount=float(p.amount),
            status=p.status.value,
            gateway_transaction_id=p.gateway_transaction_id,
            paid_at=p.paid_at,
            user_name=p.booking.user.name if p.booking and p.booking.user else None,
            user_email=p.booking.user.email if p.booking and p.booking.user else None,
            event_title=p.booking.event.title if p.booking and p.booking.event else None,
            booking_status=p.booking.status.value if p.booking else "unknown",
        )
        for p in payments
    ]
