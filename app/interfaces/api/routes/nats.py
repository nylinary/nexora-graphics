"""NATS testing routes."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.core.di.containers import Container
from app.infrastructure.messaging.nats_publisher import NATSPublisher

router = APIRouter(prefix="/nats", tags=["nats"])


@router.post("/publish")
@inject
async def publish_test_message(
    subject: str = "template.test",
    message: dict = {"test": "message", "from": "api"},
    nats_publisher: NATSPublisher = Depends(Provide[Container.nats_publisher]),
) -> dict:
    """Publish test message to NATS.

    Args:
        subject: NATS subject to publish to
        message: Message data as dictionary
        nats_publisher: NATS publisher injected via DI

    Returns:
        Success response with published message details
    """
    await nats_publisher.publish(subject, message)
    return {
        "status": "success",
        "message": "Message published",
        "subject": subject,
        "data": message,
    }
