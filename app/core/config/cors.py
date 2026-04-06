"""CORS-specific settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CORSSettings(BaseSettings):
    """CORS settings repository."""

    allow_origins: list[str] = Field(
        default=["*"],
        description="List of allowed origins",
    )
    allow_credentials: bool = Field(
        default=True,
        description="Allow credentials",
    )
    allow_methods: list[str] = Field(
        default=["*"],
        description="List of allowed HTTP methods",
    )
    allow_headers: list[str] = Field(
        default=["*"],
        description="List of allowed HTTP headers",
    )

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
    )
