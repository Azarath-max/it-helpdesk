from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "IT Helpdesk API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://helpdesk:helpdesk@localhost:5433/helpdesk"
    app_base_url: str = "http://127.0.0.1:5173"
    session_secret: str = "dev-only-change-me"
    webhook_secret: str = "dev-only-change-me"
    session_ttl_days: int = Field(default=14, ge=1, le=90)
    rate_limit_enabled: bool = True
    auth_rate_limit: int = Field(default=30, ge=1)
    webhook_rate_limit: int = Field(default=60, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    password_reset_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "helpdesk@example.com"
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False

    @model_validator(mode="after")
    def reject_default_secrets_in_production(self) -> "Settings":
        if self.environment == "production" and "dev-only-change-me" in {
            self.session_secret,
            self.webhook_secret,
        }:
            raise ValueError("SESSION_SECRET and WEBHOOK_SECRET must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
