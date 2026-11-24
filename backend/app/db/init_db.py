import datetime
import logging
from sqlalchemy import select
from app.core.database import engine, Base, AsyncSessionLocal
from app.models import Event, Seat, SeatStatus

logger = logging.getLogger("init_db")

async def init_database():
    """Initializes tables and seeds initial demo data if the DB is empty."""
    async with engine.begin() as conn:
        # Create all tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if events already exist
        result = await session.execute(select(Event))
        existing_event = result.scalars().first()

        if not existing_event:
            logger.info("No events found. Seeding demo event and seating grid...")
            demo_event = Event(
                title="Starlight Cyber Symphony 2026",
                description="An immersive audiovisual orchestral performance featuring generative modular synths and holographic visuals.",
                venue_name="Neo-Tokyo Grand Arena",
                event_date=datetime.datetime.utcnow() + datetime.timedelta(days=14),
                total_rows=6,
                seats_per_row=10,
                base_price=65.0,
            )
            session.add(demo_event)
            await session.flush()

            # Seed 60 seats (Rows A to F, Seats 1 to 10)
            rows = ["A", "B", "C", "D", "E", "F"]
            seats = []
            for row in rows:
                tier = "VIP" if row in ["A", "B"] else ("Premium" if row in ["C", "D"] else "Standard")
                price_mult = 1.8 if tier == "VIP" else (1.3 if tier == "Premium" else 1.0)
                price = round(demo_event.base_price * price_mult, 2)

                for seat_num in range(1, 11):
                    seat = Seat(
                        event_id=demo_event.id,
                        row=row,
                        seat_number=seat_num,
                        tier=tier,
                        price=price,
                        status=SeatStatus.AVAILABLE,
                    )
                    seats.append(seat)

            session.add_all(seats)
            await session.commit()
            logger.info(f"Database seeded with event '{demo_event.title}' and {len(seats)} seats.")
        else:
            logger.info("Database already initialized with events.")
