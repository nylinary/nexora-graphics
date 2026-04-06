"""Message handler interface."""

from abc import ABC, abstractmethod


class IMessageHandler(ABC):
    """Interface for NATS message handlers."""

    @abstractmethod
    async def handle(self, message_data: dict) -> None:
        """Handle incoming NATS message.

        Args:
            message_data: Parsed JSON message data as dictionary

        Raises:
            Exception: If message processing fails
        """
        pass
