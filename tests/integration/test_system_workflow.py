"""Integration tests for system effect workflows.

This module tests system effects (GetCurrentTime, GenerateUUID) using
run_ws_program. These effects don't require external infrastructure
but are tested via the full workflow pattern for consistency.
"""

from collections.abc import Generator
from datetime import datetime
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.result import Err, Ok
from effectful.effects.system import GenerateUUID, GetCurrentTime
from effectful.effects.websocket import SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestSystemWorkflowIntegration:
    """Integration tests for system effect workflows."""

    @pytest.mark.asyncio
    async def test_get_current_time_workflow(self, mocker: MockerFixture) -> None:
        """Workflow retrieves current time via system effect."""
        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow
        def get_time_program() -> Generator[AllEffects, EffectResult, datetime]:
            current_time = yield GetCurrentTime()
            assert isinstance(current_time, datetime)

            yield SendText(text=f"Current time: {current_time.isoformat()}")
            return current_time

        # Act
        before = datetime.now()
        result = await run_ws_program(get_time_program(), interpreter)
        after = datetime.now()

        # Assert
        match result:
            case Ok(time_result):
                # Time should be between before and after
                assert isinstance(time_result, datetime)
                # Compare as naive datetimes (remove tz info)
                time_naive = time_result.replace(tzinfo=None)
                assert before <= time_naive <= after
                mock_ws.send_text.assert_called_once()
            case Err(error):
                pytest.fail(f"Expected Ok(datetime), got Err({error})")

    @pytest.mark.asyncio
    async def test_generate_uuid_workflow(self, mocker: MockerFixture) -> None:
        """Workflow generates UUID via system effect."""
        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow
        def generate_uuid_program() -> Generator[AllEffects, EffectResult, UUID]:
            new_uuid = yield GenerateUUID()
            assert isinstance(new_uuid, UUID)

            yield SendText(text=f"Generated UUID: {new_uuid}")
            return new_uuid

        # Act
        result = await run_ws_program(generate_uuid_program(), interpreter)

        # Assert
        match result:
            case Ok(uuid_result):
                assert isinstance(uuid_result, UUID)
                # UUID should be valid v4
                assert uuid_result.version == 4
                mock_ws.send_text.assert_called_once()
                call_arg = mock_ws.send_text.call_args[0][0]
                assert str(uuid_result) in call_arg
            case Err(error):
                pytest.fail(f"Expected Ok(UUID), got Err({error})")

    @pytest.mark.asyncio
    async def test_multiple_uuids_unique(self, mocker: MockerFixture) -> None:
        """Workflow generates multiple unique UUIDs."""
        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow
        def multi_uuid_program() -> Generator[AllEffects, EffectResult, list[UUID]]:
            uuids: list[UUID] = []
            for _ in range(5):
                new_uuid = yield GenerateUUID()
                assert isinstance(new_uuid, UUID)
                uuids.append(new_uuid)

            yield SendText(text=f"Generated {len(uuids)} UUIDs")
            return uuids

        # Act
        result = await run_ws_program(multi_uuid_program(), interpreter)

        # Assert
        match result:
            case Ok(uuid_list):
                assert len(uuid_list) == 5
                # All UUIDs should be unique
                assert len(set(uuid_list)) == 5
                mock_ws.send_text.assert_called_once_with("Generated 5 UUIDs")
            case Err(error):
                pytest.fail(f"Expected Ok(list), got Err({error})")

    @pytest.mark.asyncio
    async def test_time_and_uuid_combined_workflow(self, mocker: MockerFixture) -> None:
        """Workflow using both time and UUID system effects."""
        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow
        def combined_program() -> Generator[AllEffects, EffectResult, str]:
            # Generate UUID for request ID
            request_id = yield GenerateUUID()
            assert isinstance(request_id, UUID)

            # Get timestamp
            timestamp = yield GetCurrentTime()
            assert isinstance(timestamp, datetime)

            # Log request
            log_msg = f"Request {request_id} at {timestamp.isoformat()}"
            yield SendText(text=log_msg)

            return str(request_id)

        # Act
        result = await run_ws_program(combined_program(), interpreter)

        # Assert
        match result:
            case Ok(request_id_str):
                # Should be valid UUID string
                UUID(request_id_str)  # Will raise if invalid
                mock_ws.send_text.assert_called_once()
                call_arg = mock_ws.send_text.call_args[0][0]
                assert request_id_str in call_arg
                assert "Request" in call_arg
            case Err(error):
                pytest.fail(f"Expected Ok(str), got Err({error})")

    @pytest.mark.asyncio
    async def test_time_progression_workflow(self, mocker: MockerFixture) -> None:
        """Workflow demonstrates time progression between calls."""
        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow that gets time twice
        def time_progression_program() -> Generator[AllEffects, EffectResult, bool]:
            time1 = yield GetCurrentTime()
            assert isinstance(time1, datetime)

            # Small delay to ensure time changes
            # Note: This is a blocking call in the generator, but demonstrates the pattern

            time2 = yield GetCurrentTime()
            assert isinstance(time2, datetime)

            # Time2 should be >= time1
            progressed = time2 >= time1
            yield SendText(text=f"Time progressed: {progressed}")
            return progressed

        # Act
        result = await run_ws_program(time_progression_program(), interpreter)

        # Assert
        match result:
            case Ok(progressed):
                assert progressed is True
                mock_ws.send_text.assert_called_once_with("Time progressed: True")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")
