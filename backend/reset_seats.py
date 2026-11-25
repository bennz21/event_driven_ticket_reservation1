import asyncio
from app.core.database import engine
from sqlalchemy import text
from app.core.events import get_event_bus, DomainEvent, EventType

async def reset_seats():
    print("Resetting all seats in main_reservation...")
    async with engine.begin() as conn:
        result = await conn.execute(
            text("UPDATE seats SET status = 'available', held_by_session_id = NULL, held_until = NULL;")
        )
        print(f"-> Successfully updated {result.rowcount} seats to 'available'!")

    # Optionally broadcast event so UI updates immediately without browser refresh
    try:
        event_bus = get_event_bus()
        await event_bus.start()
        # Broadcast release for event 1
        await event_bus.publish(
            DomainEvent(
                event_type=EventType.SEAT_RELEASED,
                event_model_id=1,
                payload={"seat_ids": list(range(1, 61)), "reason": "admin_reset"},
            )
        )
        await event_bus.stop()
    except Exception as e:
        pass

    await engine.dispose()
    print("Done! Refresh your browser or check the frontend.")

if __name__ == "__main__":
    asyncio.run(reset_seats())
