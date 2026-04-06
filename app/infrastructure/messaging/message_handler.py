"""Default message handler implementation."""

from aiologger import Logger  # type: ignore

from app.domain.interfaces.messaging.message_handler import IMessageHandler


class DefaultMessageHandler(IMessageHandler):
    """Default message handler that logs messages.

    This is a template implementation. Replace with your own handler
    that implements IMessageHandler interface.
    """

    def __init__(self, logger: Logger):
        """Initialize default message handler.

        Args:
            logger: Logger instance
        """
        self._logger = logger

    async def handle(self, message_data: dict) -> None:
        """Handle incoming NATS message.

        Args:
            message_data: Parsed JSON message data as dictionary

        Note:
            This is a template implementation. Override this method
            or create a new handler class to implement your business logic.
        """
        import asyncio

        message_id = message_data.get("message_id", "unknown")
        await self._logger.info(
            f"Default message handler received: message_id={message_id}",
            extra={"component": "message_handler", "message_id": message_id},
        )

        # Simulate processing time to demonstrate parallel processing
        await asyncio.sleep(0.1)

        await self._logger.info(
            f"Default message handler completed: message_id={message_id}",
            extra={"component": "message_handler", "message_id": message_id},
        )

        # TODO: Implement your message processing logic here
        # Example:
        # processed_data = YourSchema.model_validate(message_data)
        # await your_service.process(processed_data)
