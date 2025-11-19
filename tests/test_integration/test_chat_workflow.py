"""Integration tests for complete chat workflows.

This module tests complete user workflows combining multiple effects:
- User authentication and lookup
- Message sending and persistence
- Cache operations
- WebSocket communication

These integration tests verify that all interpreters work together correctly
when orchestrated by run_ws_program.
"""

from collections.abc import Generator
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture

from functional_effects.algebraic.result import Err, Ok
from functional_effects.domain.cache_result import CacheHit, CacheMiss
from functional_effects.domain.message import ChatMessage
from functional_effects.domain.profile import ProfileData
from functional_effects.domain.user import User, UserFound, UserNotFound
from functional_effects.effects.cache import GetCachedProfile, PutCachedProfile
from functional_effects.effects.database import GetUserById, SaveChatMessage
from functional_effects.effects.websocket import Close, CloseNormal, SendText
from functional_effects.infrastructure.cache import ProfileCache
from functional_effects.infrastructure.repositories import ChatMessageRepository, UserRepository
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.interpreters.composite import create_composite_interpreter
from functional_effects.interpreters.errors import DatabaseError
from functional_effects.programs.program_types import AllEffects, EffectResult
from functional_effects.programs.runners import run_ws_program


class TestChatWorkflowIntegration:
    """Integration tests for complete chat workflows."""

    @pytest.mark.asyncio()
    async def test_greet_user_workflow(self, mocker: MockerFixture) -> None:
        """Complete workflow: lookup user, send personalized greeting, save message."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # Seed user data
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")
        mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

        # Track saved message
        saved_message = ChatMessage(
            id=uuid4(), user_id=user_id, text="Hello Alice!", created_at=datetime.now()
        )
        mock_msg_repo.save_message.return_value = saved_message

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define complete workflow
        def greet_user_program(
            user_id: UUID,
        ) -> Generator[AllEffects, EffectResult, bool]:
            """Greet user by name and save greeting message."""
            # 1. Lookup user
            user_result = yield GetUserById(user_id=user_id)

            match user_result:
                case None:
                    yield SendText(text="Error: User not found")
                    return False
                case User(name=name):
                    # 2. Send personalized greeting
                    greeting = f"Hello {name}!"
                    yield SendText(text=greeting)

                    # 3. Save greeting to message history
                    message = yield SaveChatMessage(user_id=user_id, text=greeting)
                    assert isinstance(message, ChatMessage)

                    # 4. Confirm success
                    yield SendText(text=f"Message saved with ID: {message.id}")
                    return True
                case _:
                    return False

        # Act
        result = await run_ws_program(greet_user_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                # Verify WebSocket calls
                assert mock_ws.send_text.call_count == 2
                mock_ws.send_text.assert_any_call("Hello Alice!")
                mock_ws.send_text.assert_any_call(f"Message saved with ID: {saved_message.id}")
                # Verify database operations
                mock_user_repo.get_by_id.assert_called_once_with(user_id)
                mock_msg_repo.save_message.assert_called_once_with(user_id, "Hello Alice!")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio()
    async def test_user_not_found_workflow(self, mocker: MockerFixture) -> None:
        """Workflow handles user not found gracefully."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # User not found
        nonexistent_id = uuid4()
        mock_user_repo.get_by_id.return_value = UserNotFound(
            user_id=nonexistent_id, reason="does_not_exist"
        )

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow
        def greet_user_program(
            user_id: UUID,
        ) -> Generator[AllEffects, EffectResult, bool]:
            user_result = yield GetUserById(user_id=user_id)
            match user_result:
                case None:
                    yield SendText(text="Error: User not found")
                    return False
                case User(name=name):
                    yield SendText(text=f"Hello {name}!")
                    return True
                case _:
                    return False

        # Act
        result = await run_ws_program(greet_user_program(nonexistent_id), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is False
                mock_ws.send_text.assert_called_once_with("Error: User not found")
                mock_msg_repo.save_message.assert_not_called()
            case Err(error):
                pytest.fail(f"Expected Ok(False), got Err({error})")

    @pytest.mark.asyncio()
    async def test_cache_and_database_workflow(self, mocker: MockerFixture) -> None:
        """Workflow using both cache and database effects."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # Seed user
        user_id = uuid4()
        user = User(id=user_id, email="bob@example.com", name="Bob")
        mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

        # First call: cache miss, then cache put
        profile = ProfileData(id=str(user_id), name="Bob")
        mock_cache.get_profile.side_effect = [
            CacheMiss(key=str(user_id), reason="not_found"),  # First call: miss
            CacheHit(value=profile, ttl_remaining=300),  # Second call: hit
        ]

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow
        def cache_aware_greeting(
            user_id: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            """Check cache first, fallback to database, update cache."""
            # 1. Try cache first
            cached_profile = yield GetCachedProfile(user_id=user_id)

            match cached_profile:
                case None:
                    # 2. Cache miss - fetch from database
                    user_result = yield GetUserById(user_id=user_id)
                    match user_result:
                        case None:
                            yield SendText(text="User not found")
                            return "not_found"
                        case User(id=uid, name=name):
                            # 3. Update cache with ProfileData
                            profile = ProfileData(id=str(uid), name=name)
                            yield PutCachedProfile(user_id=user_id, profile_data=profile)
                            yield SendText(text=f"Hello {name} (from DB, cached)")
                            return "db_hit"
                        case _:
                            return "error"
                case ProfileData(name=name):
                    # Cache hit
                    yield SendText(text=f"Hello {name} (from cache)")
                    return "cache_hit"
                case _:
                    return "error"

        # Act - First call (cache miss)
        result1 = await run_ws_program(cache_aware_greeting(user_id), interpreter)

        # Assert first call
        match result1:
            case Ok(outcome):
                assert outcome == "db_hit"
                mock_ws.send_text.assert_called_once_with("Hello Bob (from DB, cached)")
                mock_cache.put_profile.assert_called_once_with(user_id, profile, 300)
            case Err(error):
                pytest.fail(f"Expected Ok('db_hit'), got Err({error})")

        # Reset call counts
        mock_ws.reset_mock()

        # Act - Second call (cache hit)
        result2 = await run_ws_program(cache_aware_greeting(user_id), interpreter)

        # Assert second call
        match result2:
            case Ok(outcome):
                assert outcome == "cache_hit"
                mock_ws.send_text.assert_called_once_with("Hello Bob (from cache)")
                # Database not called on cache hit
                assert mock_user_repo.get_by_id.call_count == 1  # Only from first call
            case Err(error):
                pytest.fail(f"Expected Ok('cache_hit'), got Err({error})")

    @pytest.mark.asyncio()
    async def test_multi_message_conversation(self, mocker: MockerFixture) -> None:
        """Workflow with multiple messages in a conversation."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        user_id = uuid4()

        # Configure message saving to return different messages
        messages_data = [
            "Welcome to the chat!",
            "How can I help you today?",
            "Type 'help' for commands.",
        ]
        saved_messages = [
            ChatMessage(id=uuid4(), user_id=user_id, text=text, created_at=datetime.now())
            for text in messages_data
        ]
        mock_msg_repo.save_message.side_effect = saved_messages

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow
        def conversation_program(
            user_id: UUID,
        ) -> Generator[AllEffects, EffectResult, int]:
            """Multi-turn conversation with message persistence."""
            messages = [
                "Welcome to the chat!",
                "How can I help you today?",
                "Type 'help' for commands.",
            ]

            for msg_text in messages:
                # Send message
                yield SendText(text=msg_text)

                # Save to history
                message = yield SaveChatMessage(user_id=user_id, text=msg_text)
                assert isinstance(message, ChatMessage)

            # Close connection
            yield Close(reason=CloseNormal())

            return len(messages)

        # Act
        result = await run_ws_program(conversation_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(message_count):
                assert message_count == 3
                # Verify all messages sent
                assert mock_ws.send_text.call_count == 3
                mock_ws.send_text.assert_any_call("Welcome to the chat!")
                mock_ws.send_text.assert_any_call("How can I help you today?")
                mock_ws.send_text.assert_any_call("Type 'help' for commands.")
                # Verify all messages saved
                assert mock_msg_repo.save_message.call_count == 3
                # Verify connection closed
                mock_ws.close.assert_called_once()
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")

    @pytest.mark.asyncio()
    async def test_workflow_error_propagation(self, mocker: MockerFixture) -> None:
        """Workflow propagates errors correctly (fail-fast)."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # Configure repository to raise error
        mock_user_repo.get_by_id.side_effect = Exception("Connection timeout")

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define workflow
        def failing_workflow(
            user_id: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            yield SendText(text="Starting workflow...")
            user_result = yield GetUserById(user_id=user_id)  # Will fail!
            # Never reached:
            match user_result:
                case User(name=name):
                    yield SendText(text=f"Hello {name}")
                    return "success"
                case _:
                    return "not_found"

        # Act
        result = await run_ws_program(failing_workflow(uuid4()), interpreter)

        # Assert
        match result:
            case Err(error):
                # Verify error type and message
                assert isinstance(error, DatabaseError)
                assert "Connection timeout" in str(error)
                # Verify workflow stopped after first message (before error)
                mock_ws.send_text.assert_called_once_with("Starting workflow...")
            case Ok(value):
                pytest.fail(f"Expected Err(DatabaseError), got Ok({value})")
