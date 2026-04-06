"""Alert entity history repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import DatabaseManager
from app.infrastructure.persistence.models.statistic import AlertEntityHistoryModel


class AlertRepository:
    """Read-only repository for alert_entity_history."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def get_alert_history(
        self,
        *,
        project_id: UUID,
        entity_type: str,
        date_from: datetime,
        date_to: datetime,
        session: AsyncSession | None = None,
    ) -> list[dict[str, object]]:
        """Fetch alert events within a date range."""
        async def _run(sess: AsyncSession) -> list[dict[str, object]]:
            stmt = (
                select(AlertEntityHistoryModel)
                .where(
                    AlertEntityHistoryModel.project_id == project_id,
                    AlertEntityHistoryModel.entity_type == entity_type,
                    AlertEntityHistoryModel.triggered_at >= date_from,
                    AlertEntityHistoryModel.triggered_at <= date_to,
                )
                .order_by(AlertEntityHistoryModel.triggered_at.asc())
            )
            result = await sess.execute(stmt)
            return [
                {
                    "id": row.id,
                    "entity_id": row.entity_id,
                    "entity_type": row.entity_type,
                    "triggered_at": row.triggered_at,
                    "new_status": row.new_status,
                    "previous_status": row.previous_status,
                    "event_type": row.event_type,
                    "change": row.change,
                }
                for row in result.scalars().all()
            ]

        if session:
            return await _run(session)
        async with self._db.session() as sess:
            return await _run(sess)
