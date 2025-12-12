"""Integration tests for WebSocket workflows with real connections.

This module tests WebSocket effect workflows using run_ws_program
with real WebSocket connections. Each test spins up a real WebSocket
server and creates ephemeral clients for end-to-end testing.
"""

import asyncio
from collections.abc import Generator

import pytest
import websockets
from websockets.legacy.server import WebSocketServerProtocol

from effectful.adapters.websocket_connection import RealWebSocketConnection
from effectful.algebraic.result import Err, Ok
from effectful.effects.websocket import Close, CloseNormal, ReceiveText, SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program
from pytest_mock import MockerFixture


class TestWebSocketWorkflowIntegration:
    """Integration tests for WebSocket workflows with real connections."""

    @pytest.mark.asyncio
    async def test_send_text_workflow(self, mocker: MockerFixture) -> None:
        """Workflow sends text to real WebSocket client."""
        received_messages: list[str] = []
        server_ready = asyncio.Event()
        message_received = asyncio.Event()

        # Server handler - receives messages from the program
        async def server_handler(websocket: WebSocketServerProtocol) -> None:
            try:
                async for message in websocket:
                    received_messages.append(str(message))
                    message_received.set()
            except websockets.ConnectionClosed:
                pass

        # Start server
        async with websockets.serve(server_handler, "localhost", 0) as server:
            # Get the actual port
            sockets = list(server.sockets)
            port = sockets[0].getsockname()[1]
            server_ready.set()  # Server is now listening

            # Connect client
            async with websockets.connect(f"ws://localhost:{port}") as ws:
                # Create interpreter with real WebSocket
                real_ws = RealWebSocketConnection(ws)
                mock_user_repo = mocker.AsyncMock(spec=UserRepository)
                mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
                mock_cache = mocker.AsyncMock(spec=ProfileCache)

                interpreter = create_composite_interpreter(
                    websocket_connection=real_ws,
                    user_repo=mock_user_repo,
                    message_repo=mock_msg_repo,
                    cache=mock_cache,
                )

                # Define workflow
                def send_program() -> Generator[AllEffects, EffectResult, bool]:
                    yield SendText(text="Hello, World!")
                    return True

                # Act
                result = await run_ws_program(send_program(), interpreter)

                # Wait for message to be received
                await asyncio.wait_for(message_received.wait(), timeout=2.0)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert len(received_messages) == 1
                assert received_messages[0] == "Hello, World!"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_receive_text_workflow(self, mocker: MockerFixture) -> None:
        """Workflow receives text from real WebSocket server."""
        server_ready = asyncio.Event()
        client_connected = asyncio.Event()

        # Server handler - sends message to client
        async def server_handler(websocket: WebSocketServerProtocol) -> None:
            await client_connected.wait()
            await websocket.send("Message from server")
            # Keep connection open until client closes
            try:
                await websocket.wait_closed()
            except Exception:
                pass

        # Start server
        async with websockets.serve(server_handler, "localhost", 0) as server:
            sockets = list(server.sockets)
            port = sockets[0].getsockname()[1]
            server_ready.set()  # Server is now listening

            # Connect client
            async with websockets.connect(f"ws://localhost:{port}") as ws:
                # Signal server that client is connected
                client_connected.set()

                # Create interpreter
                real_ws = RealWebSocketConnection(ws)
                mock_user_repo = mocker.AsyncMock(spec=UserRepository)
                mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
                mock_cache = mocker.AsyncMock(spec=ProfileCache)

                interpreter = create_composite_interpreter(
                    websocket_connection=real_ws,
                    user_repo=mock_user_repo,
                    message_repo=mock_msg_repo,
                    cache=mock_cache,
                )

                # Define workflow
                def receive_program() -> Generator[AllEffects, EffectResult, str]:
                    message = yield ReceiveText()
                    assert isinstance(message, str)
                    return message

                # Act
                result = await run_ws_program(receive_program(), interpreter)

        # Assert
        match result:
            case Ok(message):
                assert message == "Message from server"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_close_workflow(self, mocker: MockerFixture) -> None:
        """Workflow closes WebSocket connection with normal closure."""
        server_ready = asyncio.Event()
        connection_closed = asyncio.Event()
        close_code: int | None = None

        # Server handler - tracks close
        async def server_handler(websocket: WebSocketServerProtocol) -> None:
            nonlocal close_code
            try:
                await websocket.wait_closed()
                close_code = websocket.close_code
            except Exception:
                pass
            finally:
                connection_closed.set()

        # Start server
        async with websockets.serve(server_handler, "localhost", 0) as server:
            sockets = list(server.sockets)
            port = sockets[0].getsockname()[1]
            server_ready.set()  # Server is now listening

            # Connect client
            async with websockets.connect(f"ws://localhost:{port}") as ws:
                # Create interpreter
                real_ws = RealWebSocketConnection(ws)
                mock_user_repo = mocker.AsyncMock(spec=UserRepository)
                mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
                mock_cache = mocker.AsyncMock(spec=ProfileCache)

                interpreter = create_composite_interpreter(
                    websocket_connection=real_ws,
                    user_repo=mock_user_repo,
                    message_repo=mock_msg_repo,
                    cache=mock_cache,
                )

                # Define workflow
                def close_program() -> Generator[AllEffects, EffectResult, bool]:
                    yield Close(reason=CloseNormal())
                    return True

                # Act
                result = await run_ws_program(close_program(), interpreter)

            # Wait for close to propagate
            await asyncio.wait_for(connection_closed.wait(), timeout=2.0)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert close_code == 1000  # Normal closure
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_bidirectional_workflow(self, mocker: MockerFixture) -> None:
        """Workflow sends and receives in both directions."""
        server_ready = asyncio.Event()
        client_connected = asyncio.Event()
        received_by_server: list[str] = []

        # Server handler - echo server
        async def server_handler(websocket: WebSocketServerProtocol) -> None:
            await client_connected.wait()
            try:
                async for message in websocket:
                    msg_str = message.decode() if isinstance(message, bytes) else str(message)
                    received_by_server.append(msg_str)
                    await websocket.send(f"Echo: {msg_str}")
            except websockets.ConnectionClosed:
                pass

        # Start server
        async with websockets.serve(server_handler, "localhost", 0) as server:
            sockets = list(server.sockets)
            port = sockets[0].getsockname()[1]
            server_ready.set()  # Server is now listening

            # Connect client
            async with websockets.connect(f"ws://localhost:{port}") as ws:
                # Signal server
                client_connected.set()

                # Create interpreter
                real_ws = RealWebSocketConnection(ws)
                mock_user_repo = mocker.AsyncMock(spec=UserRepository)
                mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
                mock_cache = mocker.AsyncMock(spec=ProfileCache)

                interpreter = create_composite_interpreter(
                    websocket_connection=real_ws,
                    user_repo=mock_user_repo,
                    message_repo=mock_msg_repo,
                    cache=mock_cache,
                )

                # Define workflow
                def echo_program() -> Generator[AllEffects, EffectResult, str]:
                    # Send message
                    yield SendText(text="Hello")

                    # Receive echo
                    response = yield ReceiveText()
                    assert isinstance(response, str)

                    return response

                # Act
                result = await run_ws_program(echo_program(), interpreter)

        # Assert
        match result:
            case Ok(response):
                assert response == "Echo: Hello"
                assert received_by_server == ["Hello"]
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_multi_message_workflow(self, mocker: MockerFixture) -> None:
        """Workflow handles multiple send/receive cycles."""
        server_ready = asyncio.Event()
        client_connected = asyncio.Event()
        message_count = 3

        # Server handler - numbered responses
        async def server_handler(websocket: WebSocketServerProtocol) -> None:
            await client_connected.wait()
            count = 0
            try:
                async for _ in websocket:
                    count += 1
                    await websocket.send(f"Response {count}")
                    if count >= message_count:
                        break
            except websockets.ConnectionClosed:
                pass

        # Start server
        async with websockets.serve(server_handler, "localhost", 0) as server:
            sockets = list(server.sockets)
            port = sockets[0].getsockname()[1]
            server_ready.set()  # Server is now listening

            # Connect client
            async with websockets.connect(f"ws://localhost:{port}") as ws:
                # Signal server
                client_connected.set()

                # Create interpreter
                real_ws = RealWebSocketConnection(ws)
                mock_user_repo = mocker.AsyncMock(spec=UserRepository)
                mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
                mock_cache = mocker.AsyncMock(spec=ProfileCache)

                interpreter = create_composite_interpreter(
                    websocket_connection=real_ws,
                    user_repo=mock_user_repo,
                    message_repo=mock_msg_repo,
                    cache=mock_cache,
                )

                # Define workflow
                def multi_program() -> Generator[AllEffects, EffectResult, list[str]]:
                    responses: list[str] = []
                    for i in range(message_count):
                        yield SendText(text=f"Message {i + 1}")
                        response = yield ReceiveText()
                        assert isinstance(response, str)
                        responses.append(response)
                    return responses

                # Act
                result = await run_ws_program(multi_program(), interpreter)

        # Assert
        match result:
            case Ok(responses):
                assert len(responses) == 3
                assert responses == ["Response 1", "Response 2", "Response 3"]
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_send_then_close_workflow(self, mocker: MockerFixture) -> None:
        """Workflow sends message then closes cleanly."""
        server_ready = asyncio.Event()
        received_messages: list[str] = []
        connection_closed = asyncio.Event()

        # Server handler
        async def server_handler(websocket: WebSocketServerProtocol) -> None:
            try:
                async for message in websocket:
                    received_messages.append(str(message))
            except websockets.ConnectionClosed:
                pass
            finally:
                connection_closed.set()

        # Start server
        async with websockets.serve(server_handler, "localhost", 0) as server:
            sockets = list(server.sockets)
            port = sockets[0].getsockname()[1]
            server_ready.set()  # Server is now listening

            # Connect client
            async with websockets.connect(f"ws://localhost:{port}") as ws:
                # Create interpreter
                real_ws = RealWebSocketConnection(ws)
                mock_user_repo = mocker.AsyncMock(spec=UserRepository)
                mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
                mock_cache = mocker.AsyncMock(spec=ProfileCache)

                interpreter = create_composite_interpreter(
                    websocket_connection=real_ws,
                    user_repo=mock_user_repo,
                    message_repo=mock_msg_repo,
                    cache=mock_cache,
                )

                # Define workflow
                def send_close_program() -> Generator[AllEffects, EffectResult, bool]:
                    yield SendText(text="Goodbye!")
                    yield Close(reason=CloseNormal())
                    return True

                # Act
                result = await run_ws_program(send_close_program(), interpreter)

            # Wait for close
            await asyncio.wait_for(connection_closed.wait(), timeout=2.0)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert received_messages == ["Goodbye!"]
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")
