"""SQLAlchemy models."""

import uuid

from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.request import Request
from app.infrastructure.persistence.database import Base


class RequestModel(Base):
    """SQLAlchemy model for requests."""

    __tablename__ = "requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
    )
    request: Mapped[dict] = mapped_column(JSONB, nullable=False)

    def to_domain(self) -> Request:
        return Request(
            id=self.id,
            user_id=self.user_id,
            payload=dict(self.request),
        )

    @classmethod
    def from_domain(cls, request: Request) -> "RequestModel":
        return cls(
            id=str(request.id),
            user_id=str(request.user_id),
            request=request.payload,
        )
