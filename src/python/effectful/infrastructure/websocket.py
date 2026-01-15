"""WebSocket connection protocol.

This module defines Protocol interface (port) for WebSocket operations.
Concrete implementations (adapters) are provided elsewhere.
"""

from typing import Protocol


class WebSocketConnection(Protocol):
    """Protocol for WebSocket connection operations."""

    async def send_text(self, text: str) -> None:
        """Send text message over WebSocket.

        Args:
            text: Message to send
        """
        ...

    async def receive_text(self) -> str:
        """Receive text message from WebSocket.

        Returns:
            Received text message
        """
        ...

    async def close(self) -> None:
        """Close the WebSocket connection."""
        ...

    async def is_open(self) -> bool:
        """Check if WebSocket connection is open.

        Returns:
            True if connection is open, False otherwise
        """
        ...
