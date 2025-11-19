"""WebSocket implementation using websockets library.

This module provides a websockets-based implementation of the WebSocketConnection protocol.
This is a production-ready adapter for real WebSocket connections.

For testing, use pytest mocks instead of this real implementation.
"""

from websockets.legacy.client import WebSocketClientProtocol

from functional_effects.infrastructure.websocket import WebSocketConnection


class RealWebSocketConnection(WebSocketConnection):
    """websockets library-based WebSocket connection.

    Implements WebSocketConnection protocol using the websockets library.
    Suitable for client-side WebSocket connections.

    Attributes:
        _ws: WebSocket client protocol connection
    """

    def __init__(self, ws: WebSocketClientProtocol) -> None:
        """Initialize connection wrapper.

        Args:
            ws: Active WebSocket client connection
        """
        self._ws = ws

    async def send_text(self, text: str) -> None:
        """Send text message over WebSocket.

        Args:
            text: Message to send
        """
        await self._ws.send(text)

    async def receive_text(self) -> str:
        """Receive text message from WebSocket.

        Returns:
            Received text message
        """
        message = await self._ws.recv()
        return str(message)

    async def close(self) -> None:
        """Close the WebSocket connection with normal closure code."""
        await self._ws.close(code=1000, reason="Normal closure")

    async def is_open(self) -> bool:
        """Check if WebSocket connection is open.

        Returns:
            True if connection is open, False otherwise
        """
        return self._ws.open
