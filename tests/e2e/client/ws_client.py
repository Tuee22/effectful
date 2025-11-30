"""WebSocket test client for E2E testing.

Provides a client that can connect to WebSocket servers and collect messages
for testing assertions.
"""

from dataclasses import dataclass, field
from typing import Self


@dataclass(frozen=True)
class E2EWebSocketClient:
    """WebSocket client for E2E testing.

    This client simulates WebSocket communication for testing effect programs.
    It collects sent and received messages for verification.

    Note: This is a mock client that stores messages in memory rather than
    making real WebSocket connections. For real connections, you would use
    the websockets library.
    """

    _sent_messages: list[str] = field(default_factory=list)
    _received_queue: list[str] = field(default_factory=list)
    _is_open: bool = True

    @classmethod
    def create(cls) -> Self:
        """Create a new E2E WebSocket client."""
        return cls()

    async def send(self, message: str) -> None:
        """Send a message (stores for later verification).

        Args:
            message: Text message to send

        Raises:
            ConnectionError: If the connection is closed
        """
        if not self._is_open:
            raise ConnectionError("WebSocket connection is closed")
        self._sent_messages.append(message)

    async def receive(self) -> str:
        """Receive a message from the queue.

        Returns:
            Next message from the queue

        Raises:
            ConnectionError: If the connection is closed
            TimeoutError: If no message is available
        """
        if not self._is_open:
            raise ConnectionError("WebSocket connection is closed")
        if not self._received_queue:
            raise TimeoutError("No message available in receive queue")
        return self._received_queue.pop(0)

    async def close(self) -> None:
        """Close the WebSocket connection."""
        # Use object.__setattr__ to set field on frozen dataclass
        object.__setattr__(self, "_is_open", False)

    async def is_open(self) -> bool:
        """Check if the connection is open."""
        return self._is_open

    async def receive_text(self) -> str:
        """Receive text message (WebSocketConnection protocol compatibility).

        Returns:
            Next message from the queue

        Raises:
            ConnectionError: If the connection is closed
            TimeoutError: If no message is available
        """
        return await self.receive()

    def queue_message(self, message: str) -> None:
        """Queue a message for receive() to return.

        Used in tests to simulate incoming messages.

        Args:
            message: Message to queue
        """
        self._received_queue.append(message)

    def get_sent_messages(self) -> list[str]:
        """Get all messages that were sent.

        Returns:
            List of sent messages in order
        """
        return list(self._sent_messages)

    def clear_sent_messages(self) -> None:
        """Clear the list of sent messages."""
        self._sent_messages.clear()

    async def send_text(self, text: str) -> None:
        """Send text message (WebSocketConnection protocol compatibility).

        Args:
            text: Text message to send
        """
        await self.send(text)
