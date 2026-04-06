"""Sentry configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SentrySettings(BaseSettings):
    """Sentry configuration."""

    dsn: str | None = Field(
        default=None,
        description="Sentry DSN for error tracking. If not set, Sentry will be disabled.",
    )
    environment: str = Field(
        default="development",
        description="Environment name for Sentry (e.g., production, staging, development)",
    )
    traces_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sample rate for performance monitoring (0.0 to 1.0)",
    )
    profiles_sample_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sample rate for profiling (0.0 to 1.0)",
    )

    model_config = SettingsConfigDict(
        env_prefix="SENTRY_",
        case_sensitive=False,
    )
