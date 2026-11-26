from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from urllib.parse import quote_plus

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Event-Driven Ticket & Seat Reservation"
    API_V1_STR: str = "/api/v1"
    
    # MySQL Database Connection Parameters
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "ticket_reservation"
    
    # Explicit DATABASE_URL (if provided, overrides separate DB_* fields)
    DATABASE_URL: Optional[str] = None
    
    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # Construct async MySQL URL
        pwd = f":{quote_plus(self.DB_PASSWORD)}" if self.DB_PASSWORD else ""
        return f"mysql+aiomysql://{self.DB_USER}{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Redis configuration for distributed locking, caching & event messaging
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS_EVENT_BUS: bool = False
    USE_REDIS_SEAT_LOCKING: bool = True
    USE_REDIS_CACHE: bool = True
    SEAT_CACHE_TTL_SECONDS: int = 30
    EVENT_CACHE_TTL_SECONDS: int = 60
    
    # Seat hold lock duration in seconds (default: 5 minutes)
    SEAT_HOLD_DURATION_SECONDS: int = 300

    # Authentication & JWT Settings
    JWT_SECRET_KEY: str = "dev-insecure-change-me-in-env-use-32-plus-bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"

    # Google & Apple OAuth Settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_PRIVATE_KEY: str = ""
    OAUTH_ALLOW_DEMO_LOGIN: bool = False
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # ── Chatbot / AI ──────────────────────────────────────────────────────────
    # Get a free key at https://ai.google.dev
    GEMINI_API_KEY: str = ""
    # Pinecone (optional — enables RAG; chatbot still works without it)
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "ticket-chatbot"

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), str(BACKEND_DIR / ".env")),
        extra="allow",
    )

settings = Settings()
