import uuid
from typing import Any

from pydantic import BaseModel


class Request(BaseModel):
    """Domain model for requests."""

    id: uuid.UUID
    user_id: uuid.UUID
    payload: dict[str, Any]
