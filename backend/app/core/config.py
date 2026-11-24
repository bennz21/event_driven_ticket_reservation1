from pydantic_settings import BaseSettings
from typing import List, Optional
from urllib.parse import quote_plus

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
    
    # Redis configuration for distributed caching & event messaging
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS_EVENT_BUS: bool = False
    
    # Seat hold lock duration in seconds (default: 5 minutes)
    SEAT_HOLD_DURATION_SECONDS: int = 300
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
