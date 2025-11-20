"""Message handling effect programs for demo app.

All programs are pure logic using the functional_effects library.
Programs yield effects and receive results directly (not wrapped in Result).
Program returns are wrapped in Result types for explicit error handling.
"""

from collections.abc import Generator
from datetime import datetime
from uuid import UUID, uuid4

from effectful.algebraic.result import Err, Ok, Result
from effectful.effects.database import GetUserById
from effectful.effects.messaging import PublishMessage
from effectful.domain.message import ChatMessage
from effectful.domain.user import User
from effectful.programs.program_types import AllEffects, EffectResult

from demo.domain.errors import AppError
from demo.domain.responses import MessageResponse


def send_message_program(
    user_id: UUID, text: str
) -> Generator[AllEffects, EffectResult, Result[MessageResponse, AppError]]:
    """Send message to chat (publish to Pulsar).

    Program flow:
    1. Validate user exists
    2. Validate message text
    3. Create message with ID and timestamp
    4. Publish message to Pulsar topic
    5. Return MessageResponse

    Args:
        user_id: UUID of user sending message
        text: Message content

    Returns:
        Result containing MessageResponse on success, or AppError on failure

    Error cases:
        - User not found (AppError.not_found)
        - Empty message text (AppError.validation_error)
        - Pulsar publish failure (returns string message ID, won't fail in demo)
    """
    # Step 1: Validate user exists
    user = yield GetUserById(user_id=user_id)

    if user is None:
        return Err(AppError.not_found(f"User {user_id} not found"))

    assert isinstance(user, User)

    # Step 2: Validate message text
    if not text or text.strip() == "":
        return Err(AppError.validation_error("Message text cannot be empty"))

    if len(text) > 10000:
        return Err(
            AppError.validation_error("Message text cannot exceed 10000 characters")
        )

    # Step 3: Create message
    message_id = uuid4()
    created_at = datetime.now()

    # Step 4: Publish to Pulsar
    # Message payload includes full context for downstream consumers
    pulsar_payload = (
        f"{message_id}|{user_id}|{user.email}|" f"{created_at.isoformat()}|{text.strip()}"
    ).encode("utf-8")

    pulsar_message_id = yield PublishMessage(
        topic="chat-messages", payload=pulsar_payload
    )
    assert isinstance(pulsar_message_id, str)

    # Step 5: Return MessageResponse
    return Ok(
        MessageResponse(
            message_id=message_id,
            user_id=user_id,
            text=text.strip(),
            created_at=created_at,
        )
    )


def get_message_program(
    message_id: UUID,
) -> Result[MessageResponse, AppError]:
    """Get message by ID (demonstration of message retrieval pattern).

    NOTE: In a real application, this would query a database or message store.
    This demo shows the pattern without implementing full message persistence.
    Since this is a demonstration that doesn't actually query anything, it's
    implemented as a pure function returning Err rather than a generator.

    Program flow:
    1. Return not_found error (no message store in demo)

    Args:
        message_id: UUID of message to retrieve

    Returns:
        Result containing MessageResponse on success, or AppError on failure

    Error cases:
        - Message not found (AppError.not_found) - always in this demo
    """
    # NOTE: This is a simplified demonstration
    # In production, you would:
    # 1. Query database for message
    # 2. Use cache-aside pattern for frequently accessed messages
    # 3. Handle message expiration/retention policies

    # For demo purposes, we return a not_found error to show the pattern
    # A real implementation would yield GetMessageById effect
    return Err(
        AppError.not_found(
            f"Message {message_id} not found (demo: use database in production)"
        )
    )
