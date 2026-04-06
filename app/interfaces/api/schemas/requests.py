"""Request schemas for API endpoints.

These are HTTP-layer DTOs — they validate raw incoming JSON.
They are intentionally separate from application Commands:
  - API schema  → validates HTTP input (may have different field names, formats)
  - Command     → typed intent passed into the service layer

Naming convention: <Entity><Action>Request
  - RequestCreateRequest — payload for POST /service/request
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class RequestCreateRequest(BaseModel):
    """Incoming payload for POST /api/v1/service/request."""

    id: uuid.UUID = Field(..., description="Client-generated idempotency UUID")
    user_id: uuid.UUID = Field(..., description="UUID of the user making the request")
    payload: dict[str, Any] = Field(..., description="Arbitrary request payload")
