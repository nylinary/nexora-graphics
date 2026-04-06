"""Authentication utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config.settings import settings

# Configure password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(
    password: str,
) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.auth.access_token_expire_minutes,
        )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm,
    )


def create_refresh_token(
    data: dict[str, Any],
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.auth.refresh_token_expire_days,
    )
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm,
    )
