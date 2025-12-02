"""Unit tests for WebSocket connection adapter.

Tests RealWebSocketConnection using pytest-mock with AsyncMock.
"""

import pytest
from pytest_mock import MockerFixture
from websockets.legacy.client import WebSocketClientProtocol

from effectful.adapters.websocket_connection import RealWebSocketConnection


class TestRealWebSocketConnection:
    """Tests for RealWebSocketConnection."""

    @pytest.mark.asyncio
    async def test_send_text_calls_ws_send(self, mocker: MockerFixture) -> None:
        """Test send_text delegates to underlying WebSocket."""
        # Setup
        mock_ws = mocker.AsyncMock(spec=WebSocketClientProtocol)
        connection = RealWebSocketConnection(mock_ws)

        # Execute
        await connection.send_text("Hello, World!")

        # Assert
        mock_ws.send.assert_called_once_with("Hello, World!")

    @pytest.mark.asyncio
    async def test_receive_text_returns_string(self, mocker: MockerFixture) -> None:
        """Test receive_text returns string from underlying WebSocket."""
        # Setup
        mock_ws = mocker.AsyncMock(spec=WebSocketClientProtocol)
        mock_ws.recv.return_value = "Received message"

        connection = RealWebSocketConnection(mock_ws)

        # Execute
        result = await connection.receive_text()

        # Assert
        assert result == "Received message"
        mock_ws.recv.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_text_converts_to_string(self, mocker: MockerFixture) -> None:
        """Test receive_text converts non-string messages to string."""
        # Setup
        mock_ws = mocker.AsyncMock(spec=WebSocketClientProtocol)
        mock_ws.recv.return_value = b"Binary message"  # bytes

        connection = RealWebSocketConnection(mock_ws)

        # Execute
        result = await connection.receive_text()

        # Assert
        assert isinstance(result, str)
        assert "Binary message" in result

    @pytest.mark.asyncio
    async def test_close_calls_ws_close_with_normal_code(self, mocker: MockerFixture) -> None:
        """Test close calls underlying WebSocket with code 1000."""
        # Setup
        mock_ws = mocker.AsyncMock(spec=WebSocketClientProtocol)
        connection = RealWebSocketConnection(mock_ws)

        # Execute
        await connection.close()

        # Assert
        mock_ws.close.assert_called_once_with(code=1000, reason="Normal closure")

    @pytest.mark.asyncio
    async def test_is_open_returns_true_when_open(self, mocker: MockerFixture) -> None:
        """Test is_open returns True when WebSocket is open."""
        # Setup
        mock_ws = mocker.AsyncMock(spec=WebSocketClientProtocol)
        mock_ws.open = True

        connection = RealWebSocketConnection(mock_ws)

        # Execute
        result = await connection.is_open()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_is_open_returns_false_when_closed(self, mocker: MockerFixture) -> None:
        """Test is_open returns False when WebSocket is closed."""
        # Setup
        mock_ws = mocker.AsyncMock(spec=WebSocketClientProtocol)
        mock_ws.open = False

        connection = RealWebSocketConnection(mock_ws)

        # Execute
        result = await connection.is_open()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_send_operations(self, mocker: MockerFixture) -> None:
        """Test multiple send operations work correctly."""
        # Setup
        mock_ws = mocker.AsyncMock(spec=WebSocketClientProtocol)
        connection = RealWebSocketConnection(mock_ws)

        # Execute
        await connection.send_text("Message 1")
        await connection.send_text("Message 2")
        await connection.send_text("Message 3")

        # Assert
        assert mock_ws.send.call_count == 3
        mock_ws.send.assert_any_call("Message 1")
        mock_ws.send.assert_any_call("Message 2")
        mock_ws.send.assert_any_call("Message 3")

    @pytest.mark.asyncio
    async def test_multiple_receive_operations(self, mocker: MockerFixture) -> None:
        """Test multiple receive operations return correct values."""
        # Setup
        mock_ws = mocker.AsyncMock(spec=WebSocketClientProtocol)
        mock_ws.recv.side_effect = ["First", "Second", "Third"]

        connection = RealWebSocketConnection(mock_ws)

        # Execute
        result1 = await connection.receive_text()
        result2 = await connection.receive_text()
        result3 = await connection.receive_text()

        # Assert
        assert result1 == "First"
        assert result2 == "Second"
        assert result3 == "Third"
        assert mock_ws.recv.call_count == 3
