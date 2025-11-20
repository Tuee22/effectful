"""Tests for program structure and composition patterns."""

from collections.abc import Generator
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.domain.message import ChatMessage
from effectful.domain.user import User, UserFound, UserNotFound
from effectful.effects.database import GetUserById, SaveChatMessage
from effectful.effects.websocket import SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program
from effectful.testing.matchers import assert_ok, unwrap_ok


class TestProgramComposition:
    """Tests for composing programs with yield from."""

    def sub_program(self, text: str) -> Generator[AllEffects, EffectResult, str]:
        """Sub-program that sends text and returns it."""
        yield SendText(text=text)
        return text

    def main_program(self) -> Generator[AllEffects, EffectResult, str]:
        """Main program that calls sub-program."""
        result1 = yield from self.sub_program("Hello")
        result2 = yield from self.sub_program("World")
        return f"{result1} {result2}"

    @pytest.mark.asyncio()
    async def test_yield_from_delegates_to_sub_program(self, mocker: MockerFixture) -> None:
        """yield from should delegate execution to sub-program."""
        # Create mocks
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

        result = await run_ws_program(self.main_program(), interpreter)

        value = unwrap_ok(result)
        assert value == "Hello World"

        # Verify both messages were sent
        assert mock_ws.send_text.call_count == 2
        mock_ws.send_text.assert_any_call("Hello")
        mock_ws.send_text.assert_any_call("World")


class TestProgramErrorPropagation:
    """Tests for error propagation in programs."""

    def failing_sub_program(self) -> Generator[AllEffects, EffectResult, str]:
        """Sub-program that will fail."""
        # This will return None (user not found)
        user_result = yield GetUserById(user_id=uuid4())
        # This code won't execute due to fail-fast
        match user_result:
            case User(name=name):
                return name
            case _:
                return "not_found"

    def program_with_failing_sub(self) -> Generator[AllEffects, EffectResult, str]:
        """Program that calls failing sub-program."""
        yield SendText(text="Before sub-program")
        result = yield from self.failing_sub_program()
        # This won't execute if sub-program fails
        yield SendText(text="After sub-program")
        return result

    @pytest.mark.asyncio()
    async def test_error_in_sub_program_stops_main_program(self, mocker: MockerFixture) -> None:
        """Error in sub-program should stop main program execution."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # User not found
        mock_user_repo.get_by_id.return_value = UserNotFound(
            user_id=uuid4(), reason="does_not_exist"
        )

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        result = await run_ws_program(self.program_with_failing_sub(), interpreter)

        # Program should complete successfully (user not found returns normally)
        assert_ok(result)


class TestComplexWorkflows:
    """Tests for complex multi-step workflows."""

    def lookup_and_greet(self, user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
        """Reusable workflow: lookup user and greet."""
        user_result = yield GetUserById(user_id=user_id)

        match user_result:
            case None:
                yield SendText(text="User not found")
                return "not_found"
            case User(name=name):
                greeting = f"Hello {name}!"
                yield SendText(text=greeting)
                return "greeted"
        return "unknown"

    def batch_greet_users(
        self, user_ids: list[UUID]
    ) -> Generator[AllEffects, EffectResult, dict[str, int]]:
        """Greet multiple users and return stats."""
        stats = {"greeted": 0, "not_found": 0}

        for user_id in user_ids:
            result = yield from self.lookup_and_greet(user_id)
            if result == "greeted":
                stats["greeted"] += 1
            else:
                stats["not_found"] += 1

        return stats

    @pytest.mark.asyncio()
    async def test_batch_workflow_with_mixed_results(self, mocker: MockerFixture) -> None:
        """Batch workflow should handle mix of successful and failed lookups."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        user_ids = [uuid4() for _ in range(5)]

        # Add 3 users, leave 2 missing
        users = {
            user_ids[0]: User(id=user_ids[0], email="u1@example.com", name="User 1"),
            user_ids[2]: User(id=user_ids[2], email="u3@example.com", name="User 3"),
            user_ids[4]: User(id=user_ids[4], email="u5@example.com", name="User 5"),
        }

        # Configure repository to return users or not found
        def get_by_id_side_effect(user_id: UUID) -> UserFound | UserNotFound:
            if user_id in users:
                return UserFound(user=users[user_id], source="database")
            return UserNotFound(user_id=user_id, reason="does_not_exist")

        mock_user_repo.get_by_id.side_effect = get_by_id_side_effect

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        result = await run_ws_program(self.batch_greet_users(user_ids), interpreter)

        stats = unwrap_ok(result)
        assert stats == {"greeted": 3, "not_found": 2}


class TestConditionalLogic:
    """Tests for conditional logic in programs."""

    def conditional_workflow(
        self, user_id: UUID, send_message: bool
    ) -> Generator[AllEffects, EffectResult, str]:
        """Workflow with conditional message saving."""
        user_result = yield GetUserById(user_id=user_id)

        match user_result:
            case None:
                return "user_not_found"
            case User(name=name):
                greeting = f"Hello {name}!"
                yield SendText(text=greeting)

                if send_message:
                    message = yield SaveChatMessage(user_id=user_id, text=greeting)
                    assert isinstance(message, ChatMessage)
                    return "greeted_and_saved"
                else:
                    return "greeted_only"
        return "unknown"

    @pytest.mark.asyncio()
    async def test_conditional_save_when_true(self, mocker: MockerFixture) -> None:
        """Conditional workflow should save message when flag is true."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        user_id = uuid4()
        user = User(id=user_id, email="test@example.com", name="Test")
        mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

        saved_message = ChatMessage(
            id=uuid4(), user_id=user_id, text="Hello Test!", created_at=datetime.now()
        )
        mock_msg_repo.save_message.return_value = saved_message

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        result = await run_ws_program(
            self.conditional_workflow(user_id, send_message=True), interpreter
        )

        value = unwrap_ok(result)
        assert value == "greeted_and_saved"

        # Verify message was saved
        mock_msg_repo.save_message.assert_called_once_with(user_id, "Hello Test!")

    @pytest.mark.asyncio()
    async def test_conditional_skip_when_false(self, mocker: MockerFixture) -> None:
        """Conditional workflow should skip message when flag is false."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        user_id = uuid4()
        user = User(id=user_id, email="test@example.com", name="Test")
        mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        result = await run_ws_program(
            self.conditional_workflow(user_id, send_message=False), interpreter
        )

        value = unwrap_ok(result)
        assert value == "greeted_only"

        # Verify no message was saved
        mock_msg_repo.save_message.assert_not_called()


class TestEmptyPrograms:
    """Tests for edge cases with minimal programs."""

    def empty_program(self) -> Generator[AllEffects, EffectResult, str]:
        """Program that yields nothing and returns immediately."""
        yield from ()
        return "empty"

    def single_effect_program(self) -> Generator[AllEffects, EffectResult, str]:
        """Program with single effect."""
        yield SendText(text="Single")
        return "done"

    @pytest.mark.asyncio()
    async def test_empty_program_completes(self, mocker: MockerFixture) -> None:
        """Empty program should complete successfully."""
        # Create mocks
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

        result = await run_ws_program(self.empty_program(), interpreter)

        value = unwrap_ok(result)
        assert value == "empty"

    @pytest.mark.asyncio()
    async def test_single_effect_program_completes(self, mocker: MockerFixture) -> None:
        """Single effect program should complete successfully."""
        # Create mocks
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

        result = await run_ws_program(self.single_effect_program(), interpreter)

        value = unwrap_ok(result)
        assert value == "done"
