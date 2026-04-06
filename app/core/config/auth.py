"""Authentication related settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """Authentication settings."""

    # JWT settings
    secret_key: str = Field(
        default="supersecret",
        description="Secret key for JWT tokens",
    )
    algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT tokens",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days",
    )

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
    )
