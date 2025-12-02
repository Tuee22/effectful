"""Example 02: User Greeting

Effect program demonstrating database lookup and WebSocket communication.

Run:
    python -m examples.02_user_greeting
"""

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4
from unittest.mock import AsyncMock

from effectful import (
    AllEffects,
    ChatMessage,
    EffectResult,
    GetUserById,
    SaveChatMessage,
    SendText,
    User,
    UserNotFound,
    run_ws_program,
)
from effectful.algebraic.result import Err, Ok
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter


def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Look up user and send personalized greeting."""
    user_result = yield GetUserById(user_id=user_id)

    match user_result:
        case UserNotFound():
            yield SendText(text="Error: User not found")
            return "not_found"

        case User(name=name):
            greeting = f"Hello {name}!"
            yield SendText(text=greeting)

            message = yield SaveChatMessage(user_id=user_id, text=greeting)
            assert isinstance(message, ChatMessage)

            yield SendText(text=f"Message saved with ID: {message.id}")
            return "success"

        case _:
            return "error"


async def main() -> None:
    """Run the user greeting program."""
    user_id = uuid4()

    # Typed AsyncMocks for infrastructure (spec=Protocol per testing doctrine)
    ws = AsyncMock(spec=WebSocketConnection)
    ws.is_open.return_value = True

    user_repo = AsyncMock(spec=UserRepository)
    user_repo.get_by_id.return_value = User(id=user_id, email="alice@example.com", name="Alice")

    message_repo = AsyncMock(spec=ChatMessageRepository)
    message_repo.save_message.return_value = ChatMessage(
        id=uuid4(),
        user_id=user_id,
        text="Hello Alice!",
        created_at=datetime.now(UTC),
    )

    cache = AsyncMock(spec=ProfileCache)

    interpreter = create_composite_interpreter(
        websocket_connection=ws,
        user_repo=user_repo,
        message_repo=message_repo,
        cache=cache,
    )

    print(f"Running greet_user program for user {user_id}...")
    result = await run_ws_program(greet_user(user_id), interpreter)

    match result:
        case Ok(value):
            print(f"✓ Success: {value}")
            print(f"WebSocket send_text calls: {ws.send_text.call_count}")
            print("Messages sent:")
            for i, call in enumerate(ws.send_text.call_args_list, 1):
                print(f"  {i}. {call.args[0]}")
            print("Database get_by_id called with:", user_repo.get_by_id.call_args)
            print("Saved message ID:", message_repo.save_message.return_value.id)
        case Err(error):
            print(f"✗ Error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
