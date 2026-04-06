"""Redis settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    host: str = Field(
        default="redis",
        description="Redis host",
    )
    port: int = Field(
        default=6379,
        description="Redis port",
    )
    db: int = Field(
        default=0,
        description="Redis database number",
    )
    username: str | None = Field(
        default=None,
        description="Redis username",
    )
    password: str | None = Field(
        default=None,
        description="Redis password",
    )

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
    )

    @property
    def connection_url(self) -> str:
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        elif self.password:
            auth = f":{self.password}@"
        else:
            auth = ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

    def get_connection_url(self, db: int = 1) -> str:
        """Get Redis connection URL for specific database."""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        elif self.password:
            auth = f":{self.password}@"
        else:
            auth = ""
        return f"redis://{auth}{self.host}:{self.port}/{db}"
