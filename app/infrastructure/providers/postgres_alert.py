"""PostgreSQL implementation of IAlertProvider."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from app.domain.interfaces.providers.alert_provider import IAlertProvider
from app.domain.models.graphics import AlertEvent
from app.infrastructure.persistence.alert_repository import AlertRepository


class PostgresAlertProvider(IAlertProvider):
    """Fetches alert history from PostgreSQL via AlertRepository."""

    def __init__(self, repo: AlertRepository) -> None:
        self._repo = repo

    async def fetch_alert_history(
        self,
        *,
        project_id: uuid.UUID,
        entity_type: str,
        date_from: date,
        date_to: date,
    ) -> list[AlertEvent]:
        dt_from = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        dt_to = datetime.combine(date_to, time(23, 59, 59, 999999), tzinfo=timezone.utc)

        rows = await self._repo.get_alert_history(
            project_id=project_id,
            entity_type=entity_type,
            date_from=dt_from,
            date_to=dt_to,
        )

        return [
            AlertEvent(
                entity_id=row["entity_id"],
                entity_label=str(row["entity_id"]),
                triggered_at=row["triggered_at"].date()
                if isinstance(row["triggered_at"], datetime)
                else row["triggered_at"],
                event_type=row["event_type"],
                new_status=row["new_status"],
                alert_type=row.get("event_type", "unknown"),
            )
            for row in rows
        ]
