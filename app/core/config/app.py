"""API settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APPSettings(BaseSettings):
    name: str = Field(
        default="Template App",
        description="Application name",
    )
    version: str = Field(
        default="0.1.0",
        description="Application version",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the application to",
    )
    port: int = Field(
        default=8000,
        description="Port to bind the application to",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    model_config = SettingsConfigDict(
        env_prefix="TEMPLATE_APP_",
    )

    @property
    def connection_url(self) -> str:
        return f"http://{self.host}:{self.port}"
