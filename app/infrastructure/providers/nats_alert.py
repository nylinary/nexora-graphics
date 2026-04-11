"""NATS-based implementation of IAlertProvider.

Delegates to statistics-service via NatsStatisticsClient RPC.
"""

from __future__ import annotations

import uuid
from datetime import date

from app.domain.interfaces.providers.alert_provider import IAlertProvider
from app.domain.models.graphics import AlertEvent
from app.infrastructure.messaging.nats_statistics_client import NatsStatisticsClient


class NATSAlertProvider(IAlertProvider):
    """Fetches alert history from statistics-service via NATS."""

    def __init__(self, client: NatsStatisticsClient) -> None:
        self._client = client

    async def fetch_alert_history(
        self,
        *,
        project_id: uuid.UUID,
        entity_type: str,
        date_from: date,
        date_to: date,
    ) -> list[AlertEvent]:
        data = await self._client.request("alerts.fetch", {
            "project_id": str(project_id),
            "entity_type": entity_type,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        })
        return [AlertEvent.model_validate(e) for e in data["events"]]
