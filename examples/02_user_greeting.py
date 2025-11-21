"""Example 02: User Greeting

Effect program demonstrating database lookup and WebSocket communication.

Run:
    python -m examples.02_user_greeting
"""

import asyncio
from collections.abc import Generator
from uuid import UUID, uuid4

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
from effectful.testing import FakeUserRepository, create_test_interpreter


def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Look up user and send personalized greeting.

    Args:
        user_id: User to greet

    Yields:
        GetUserById, SendText, SaveChatMessage effects

    Returns:
        Status message ("success" | "not_found")
    """
    # Look up user
    user_result = yield GetUserById(user_id=user_id)

    # Pattern match on result
    match user_result:
        case UserNotFound():
            # User not found
            yield SendText(text="Error: User not found")
            return "not_found"

        case User(name=name):
            # User found - send greeting
            greeting = f"Hello {name}!"
            yield SendText(text=greeting)

            # Save greeting as chat message
            message = yield SaveChatMessage(user_id=user_id, text=greeting)

            # Type narrowing
            assert isinstance(message, ChatMessage)

            # Confirm save
            yield SendText(text=f"Message saved with ID: {message.id}")

            return "success"

        case unexpected:
            raise AssertionError(f"Unexpected type: {type(unexpected)}")


async def main() -> None:
    """Run the user greeting program."""
    # Setup test data
    fake_repo = FakeUserRepository()
    user_id = uuid4()
    fake_repo._users[user_id] = User(id=user_id, email="alice@example.com", name="Alice")

    # Create interpreter with fake repository
    interpreter = create_test_interpreter(user_repo=fake_repo)

    print(f"Running greet_user program for user {user_id}...")

    # Run program
    result = await run_ws_program(greet_user(user_id), interpreter)

    # Handle result
    match result:
        case Ok(value):
            print(f"✓ Success: {value}")

            # Show sent messages
            websocket = interpreter._websocket._connection
            print("\nMessages sent:")
            for i, msg in enumerate(websocket._sent_messages, 1):
                print(f"  {i}. {msg}")

            # Show saved messages
            message_repo = interpreter._database._message_repo
            print(f"\nMessages saved: {len(message_repo._messages)}")
            for msg in message_repo._messages:
                print(f"  - {msg.text} (ID: {msg.id})")

        case Err(error):
            print(f"✗ Error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
