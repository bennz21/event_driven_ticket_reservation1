from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_seat_service
from app.services.seat_service import SeatService
from app.schemas import SeatResponse, SeatHoldRequest, SeatReleaseRequest, SeatHoldResult

router = APIRouter()

@router.get("/{event_id}/seats", response_model=List[SeatResponse])
async def get_event_seats(
    event_id: int,
    seat_service: SeatService = Depends(get_seat_service),
):
    """Get the current live layout and statuses of all seats for an event."""
    return await seat_service.get_seats_for_event(event_id)

@router.post("/{event_id}/seats/hold", response_model=SeatHoldResult)
async def hold_seats(
    event_id: int,
    req: SeatHoldRequest,
    seat_service: SeatService = Depends(get_seat_service),
):
    """
    Temporarily holds one or more seats for a customer session with optimistic locking.
    Triggers SEAT_HELD domain event on the event bus.
    """
    if not req.seat_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No seat IDs provided.")

    held, failed, hold_until = await seat_service.hold_seats(
        event_id=event_id,
        seat_ids=req.seat_ids,
        session_id=req.session_id,
    )

    success = len(failed) == 0
    message = (
        "Seats successfully held!"
        if success
        else f"Some seats could not be held (already taken or unavailable): {failed}"
    )

    return SeatHoldResult(
        success=success,
        held_seat_ids=held,
        failed_seat_ids=failed,
        held_until=hold_until,
        message=message,
    )

@router.post("/{event_id}/seats/release")
async def release_seats(
    event_id: int,
    req: SeatReleaseRequest,
    seat_service: SeatService = Depends(get_seat_service),
):
    """
    Releases held seats if the user cancels selection or abandons cart.
    Triggers SEAT_RELEASED domain event on the event bus.
    """
    released = await seat_service.release_seats(
        event_id=event_id,
        seat_ids=req.seat_ids,
        session_id=req.session_id,
    )
    return {"released_seat_ids": released, "message": "Seats released."}
