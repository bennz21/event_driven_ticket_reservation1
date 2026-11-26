from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from app.core.config import settings

db_url = settings.sync_database_url

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "tidbcloud.com" in db_url or settings.DB_PORT == 4000:
    # TiDB Cloud requires SSL
    connect_args["ssl"] = {"ca": "/etc/ssl/certs/ca-certificates.crt"} if not connect_args.get("ssl") else connect_args["ssl"]

engine = create_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional SQLAlchemy PyMySQL session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
