import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "IndiaGuessr"
    API_V1_STR: str = "/api/v1"
    
    # Database connection URL
    # Defaults to local async SQLite db file
    DATABASE_URL: str = "sqlite+aiosqlite:///./indiaguessr.db"
    
    # Google Maps API Key for Street View verification (optional)
    # If empty, the frontend will use fallback mock locations
    GOOGLE_MAPS_API_KEY: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if not v:
            return "sqlite+aiosqlite:///./indiaguessr.db"
        # Render and Neon provide connection URLs starting with postgres://
        # SQLAlchemy requires postgresql:// and since we use asyncpg, we need postgresql+asyncpg://
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
