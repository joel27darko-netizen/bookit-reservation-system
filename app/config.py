"""
Central application configuration.

All environment-driven settings live here so the rest of the codebase
never reads os.environ directly. This keeps configuration testable and
overridable (e.g. swapping SQLite for PostgreSQL in production simply
means changing DATABASE_URL).
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "BookIt - Reservation Management System"
    ENV: str = "development"

    # --- Database ---
    # SQLite for local/dev simplicity. Swap for a PostgreSQL DSN in prod:
    # postgresql+psycopg2://user:password@host:5432/dbname
    DATABASE_URL: str = "sqlite:///./bookit.db"

    # --- Security / JWT ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_super_secret_key_please_rotate"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours
    COOKIE_NAME: str = "bookit_access_token"

    # --- Business rules ---
    DEFAULT_SLOT_MINUTES: int = 30  # granularity used by availability engine
    CANCELLATION_WINDOW_HOURS: int = 2  # min hours before start to allow cancel

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor -- avoids re-parsing env on every call."""
    return Settings()


settings = get_settings()
