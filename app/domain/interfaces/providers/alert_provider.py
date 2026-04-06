"""Alert data provider interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import date

from app.domain.models.graphics import AlertEvent


class IAlertProvider(ABC):
    """Contract for fetching alert history."""

    @abstractmethod
    async def fetch_alert_history(
        self,
        *,
        project_id: uuid.UUID,
        entity_type: str,
        date_from: date,
        date_to: date,
    ) -> list[AlertEvent]:
        """Fetch alert events for a project within a date range."""
