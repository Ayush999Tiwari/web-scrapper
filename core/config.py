"""
Application Configuration
Loads environment variables using Pydantic Settings.
"""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_NAME: str = "WebIntel AI"
    DEBUG: bool = False
@lru_cache
def get_settings() -> Settings:
    """
    Returns cached settings instance.
    This ensures the .env file
    is only read once.
    """
    return Settings() # type: ignore