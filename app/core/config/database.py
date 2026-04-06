"""Database repository settings."""

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database repository settings."""

    dsn: PostgresDsn = Field(
        default=PostgresDsn(
            "postgresql+asyncpg://template_app_db_user:template_app_db_password@"
            "template_app_postgres:5432/template_app_db"
        ),
        description="Database connection URL",
    )
    echo: bool = Field(
        default=False,
        description="Enable SQL query logging",
    )
    pool_size: int = Field(
        default=5,
        gt=0,
        description="Size of the connection pool",
    )
    max_overflow: int = Field(
        default=10,
        gt=0,
        description="Max number of connections that can be " "created beyond pool_size",
    )
    pool_timeout: int = Field(
        default=60,
        gt=0,
        description="Number of seconds to wait before timing out on " "getting a connection from the pool",
    )
    pool_recycle: int = Field(
        default=3600,
        gt=0,
        description="Number of seconds after which to recycle connections",
    )

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
    )
