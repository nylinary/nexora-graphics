"""Main settings repository."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config.app import APPSettings
from app.core.config.auth import AuthSettings
from app.core.config.cors import CORSSettings
from app.core.config.database import DatabaseSettings
from app.core.config.nats import NATSSettings
from app.core.config.redis import RedisSettings
from app.core.config.sentry import SentrySettings


class Settings(BaseSettings):
    auth: AuthSettings = Field(
        default_factory=AuthSettings,
        description="Authentication settings",
    )
    app: APPSettings = Field(
        default_factory=APPSettings,
        description="Application settings",
    )
    cors: CORSSettings = Field(
        default_factory=CORSSettings,
        description="CORS settings",
    )
    db: DatabaseSettings = Field(
        default_factory=DatabaseSettings,
        description="Database settings",
    )
    redis: RedisSettings = Field(
        default_factory=RedisSettings,
        description="Redis settings",
    )
    nats: NATSSettings = Field(
        default_factory=NATSSettings,
        description="NATS messaging settings",
    )
    sentry: SentrySettings = Field(
        default_factory=SentrySettings,
        description="Sentry error tracking settings",
    )

    model_config = SettingsConfigDict()


settings = Settings()
