"""Message handling effect programs for demo app.

All programs are pure logic using the functional_effects library.
Programs yield effects and return Result types for explicit error handling.
"""

from collections.abc import Generator
from datetime import datetime
from uuid import UUID, uuid4

from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.effects.database import GetUserById
from functional_effects.effects.messaging import PublishMessage
from functional_effects.effects.websocket import BroadcastMessage
from functional_effects.domain.message import Message
from functional_effects.domain.user import User

from demo.domain.errors import AppError
from demo.domain.responses import MessageResponse


def send_message_program(
    user_id: UUID, text: str
) -> Generator[
    GetUserById | PublishMessage | BroadcastMessage,
    Result[User, str] | Result[str, str] | Result[bool, str],
    Result[MessageResponse, AppError],
]:
    """Send message to chat (publish to Pulsar + broadcast via WebSocket).

    Program flow:
    1. Validate user exists
    2. Validate message text
    3. Create message with ID and timestamp
    4. Publish message to Pulsar topic
    5. Broadcast message to WebSocket clients
    6. Return MessageResponse

    Args:
        user_id: UUID of user sending message
        text: Message content

    Returns:
        Result containing MessageResponse on success, or AppError on failure

    Error cases:
        - User not found (AppError.not_found)
        - Empty message text (AppError.validation_error)
        - Pulsar publish failure (AppError.internal_error)
        - WebSocket broadcast failure (non-critical, logged but not failed)
    """
    # Step 1: Validate user exists
    user_result = yield GetUserById(user_id=user_id)
    match user_result:
        case Ok(_user):
            pass
        case Err(error):
            return Err(AppError.not_found(f"User {user_id} not found: {error}"))

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

    message = Message(
        message_id=message_id,
        user_id=user_id,
        text=text.strip(),
        created_at=created_at,
    )

    # Step 4: Publish to Pulsar
    publish_result = yield PublishMessage(
        topic="chat-messages", message=message.text.encode("utf-8")
    )
    match publish_result:
        case Ok(_message_id):
            pass
        case Err(error):
            return Err(
                AppError.internal_error(f"Failed to publish message: {error}")
            )

    # Step 5: Broadcast via WebSocket (non-critical)
    broadcast_result = yield BroadcastMessage(
        event="new_message",
        payload={
            "message_id": str(message.message_id),
            "user_id": str(message.user_id),
            "text": message.text,
            "created_at": message.created_at.isoformat(),
        },
    )
    match broadcast_result:
        case Ok(_):
            pass
        case Err(_error):
            # WebSocket broadcast failure is non-critical
            # Message is already in Pulsar, clients can poll
            pass

    # Step 6: Return MessageResponse
    return Ok(
        MessageResponse(
            message_id=message.message_id,
            user_id=message.user_id,
            text=message.text,
            created_at=message.created_at,
        )
    )


def get_message_program(
    message_id: UUID,
) -> Generator[
    PublishMessage,
    Result[str, str],
    Result[MessageResponse, AppError],
]:
    """Get message by ID (demonstration of message retrieval pattern).

    NOTE: In a real application, this would query a database or message store.
    This demo shows the pattern using Pulsar's message ID lookup.

    Program flow:
    1. Query Pulsar for message by ID (simulated)
    2. Parse message content
    3. Return MessageResponse

    Args:
        message_id: UUID of message to retrieve

    Returns:
        Result containing MessageResponse on success, or AppError on failure

    Error cases:
        - Message not found (AppError.not_found)
        - Message parsing failure (AppError.internal_error)
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
