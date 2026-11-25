import asyncio
import sys
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine

async def check_connection():
    print(f"Checking database connection to:")
    print(f"  Host: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"  User: {settings.DB_USER}")
    print(f"  Database: {settings.DB_NAME}")
    print(f"  Async URL: {settings.async_database_url}")
    print("-" * 50)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1;"))
            print(f"-> SUCCESS: Database is connected and responding! Query output: {result.scalar()}")
            
            # Check existing tables and counts
            tables_result = await conn.execute(text("SHOW TABLES;"))
            tables = [row[0] for row in tables_result.fetchall()]
            print(f"-> Found tables: {tables}")
            
            if "events" in tables:
                events_count = await conn.execute(text("SELECT COUNT(*) FROM events;"))
                print(f"-> Events count: {events_count.scalar()}")
            if "seats" in tables:
                seats_count = await conn.execute(text("SELECT COUNT(*) FROM seats;"))
                print(f"-> Seats count: {seats_count.scalar()}")
    except Exception as e:
        print(f"-> FAILED: Could not connect to the database!")
        print(f"   Error: {type(e).__name__}: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_connection())
