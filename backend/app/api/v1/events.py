from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import redis_service
from app.models import Event
from app.schemas import EventResponse, EventCreate

router = APIRouter()


@router.get("", response_model=List[EventResponse])
async def list_events(db: AsyncSession = Depends(get_db)):
    """Retrieve all available events/shows."""
    cached = await redis_service.get_cached_events()
    if cached is not None:
        return [EventResponse.model_validate(item) for item in cached]

    result = await db.execute(select(Event).order_by(Event.event_date.asc()))
    events = result.scalars().all()
    serialized = [EventResponse.model_validate(e) for e in events]
    await redis_service.set_cached_events([e.model_dump(mode="json") for e in serialized])
    return serialized


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve details for a specific event."""
    cached = await redis_service.get_cached_event(event_id)
    if cached is not None:
        return EventResponse.model_validate(cached)

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    serialized = EventResponse.model_validate(event)
    await redis_service.set_cached_event(event_id, serialized.model_dump(mode="json"))
    return serialized


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(event_in: EventCreate, db: AsyncSession = Depends(get_db)):
    """Create a new event."""
    new_event = Event(**event_in.model_dump())
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    await redis_service.invalidate_events_cache(new_event.id)
    return new_event
