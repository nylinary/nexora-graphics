"""Configuration module."""

from app.core.config.app import APPSettings
from app.core.config.auth import AuthSettings
from app.core.config.redis import RedisSettings
from app.core.config.settings import Settings

__all__ = [
    "settings",
    "Settings",
    "RedisSettings",
    "APPSettings",
    "AuthSettings",
]
