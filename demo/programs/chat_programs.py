"""Complex chat workflow effect program demonstrating all 6 infrastructure types.

This module shows how to compose multiple effects across different infrastructure
layers into a single cohesive business workflow.
"""

from collections.abc import Generator
from datetime import datetime
from uuid import UUID, uuid4

from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.effects.auth import ValidateToken
from functional_effects.effects.cache import GetCachedValue, PutCachedValue
from functional_effects.effects.database import GetUserById
from functional_effects.effects.messaging import PublishMessage
from functional_effects.effects.storage import PutObject
from functional_effects.effects.websocket import BroadcastMessage
from functional_effects.domain.message import Message
from functional_effects.domain.s3_object import S3ObjectMetadata
from functional_effects.domain.token import TokenMetadata
from functional_effects.domain.user import User

from demo.domain.errors import AppError, AuthError
from demo.domain.responses import MessageResponse


def send_authenticated_message_with_storage_program(
    token: str, text: str
) -> Generator[
    ValidateToken
    | GetCachedValue
    | GetUserById
    | PutCachedValue
    | PutObject
    | PublishMessage
    | BroadcastMessage,
    Result[TokenMetadata, str]
    | Result[bytes, str]
    | Result[User, str]
    | Result[bool, str]
    | Result[S3ObjectMetadata, str]
    | Result[str, str]
    | Result[bool, str],
    Result[MessageResponse, AuthError | AppError],
]:
    """Send authenticated message with S3 archival (all 6 infrastructure types).

    This program demonstrates a complete workflow using all infrastructure:
    - Auth: JWT token validation
    - Cache: User data cache-aside pattern with Redis
    - Database: User lookup in PostgreSQL
    - Storage: Message archival to S3
    - Messaging: Publish to Pulsar topic
    - WebSocket: Real-time broadcast to connected clients

    Program flow:
    1. [Auth] Validate JWT token
    2. [Cache] Check for cached user data
    3. [Database] Load user from PostgreSQL (if cache miss)
    4. [Cache] Store user in cache for future requests
    5. [Storage] Archive message to S3 for compliance/audit
    6. [Messaging] Publish message to Pulsar topic
    7. [WebSocket] Broadcast message to connected clients
    8. Return MessageResponse

    Args:
        token: JWT access token
        text: Message content

    Returns:
        Result containing MessageResponse on success, or AuthError/AppError on failure

    Error cases:
        - Invalid/expired token (AuthError)
        - User not found (AppError.not_found)
        - Empty message (AppError.validation_error)
        - S3 storage failure (AppError.internal_error)
        - Pulsar publish failure (AppError.internal_error)
        - Cache/WebSocket failures are non-critical (logged but not failed)
    """
    # Step 1: [Auth] Validate JWT token
    validate_result = yield ValidateToken(token=token)
    match validate_result:
        case Ok(metadata):
            user_id = metadata.user_id
        case Err(error):
            return Err(
                AuthError(
                    message=f"Invalid or expired token: {error}",
                    error_type="token_invalid",
                )
            )

    # Step 2: [Cache] Check for cached user data (cache-aside pattern)
    cache_key = f"user:{user_id}"
    cached_user_result = yield GetCachedValue(key=cache_key)

    user: User
    match cached_user_result:
        case Ok(_cached_bytes):
            # Cache hit - in production, deserialize bytes to User
            # For demo, we'll still fetch from DB to show the pattern
            pass
        case Err(_error):
            # Cache miss - expected on first access
            pass

    # Step 3: [Database] Load user from PostgreSQL
    user_result = yield GetUserById(user_id=user_id)
    match user_result:
        case Ok(loaded_user):
            user = loaded_user
        case Err(error):
            return Err(AppError.not_found(f"User {user_id} not found: {error}"))

    # Step 4: [Cache] Store user in Redis for future requests (TTL: 5 minutes)
    # In production, serialize User to bytes (JSON, msgpack, etc.)
    user_cache_bytes = f"{user.email}|{user.name}".encode("utf-8")
    cache_put_result = yield PutCachedValue(
        key=cache_key, value=user_cache_bytes, ttl_seconds=300
    )
    match cache_put_result:
        case Ok(_):
            pass
        case Err(_error):
            # Cache write failure is non-critical
            pass

    # Step 5: Validate message text
    if not text or text.strip() == "":
        return Err(AppError.validation_error("Message text cannot be empty"))

    if len(text) > 10000:
        return Err(
            AppError.validation_error("Message text cannot exceed 10000 characters")
        )

    # Create message
    message_id = uuid4()
    created_at = datetime.now()

    message = Message(
        message_id=message_id,
        user_id=user.user_id,
        text=text.strip(),
        created_at=created_at,
    )

    # Step 6: [Storage] Archive message to S3 for compliance/audit
    # Object key: messages/{year}/{month}/{day}/{message_id}.txt
    s3_key = (
        f"messages/{created_at.year}/{created_at.month:02d}/"
        f"{created_at.day:02d}/{message_id}.txt"
    )
    s3_content = (
        f"Message ID: {message_id}\n"
        f"User ID: {user.user_id}\n"
        f"User Email: {user.email}\n"
        f"Created At: {created_at.isoformat()}\n\n"
        f"{message.text}"
    ).encode("utf-8")

    storage_result = yield PutObject(
        bucket="chat-archive", key=s3_key, content=s3_content
    )
    match storage_result:
        case Ok(_metadata):
            pass
        case Err(error):
            return Err(
                AppError.internal_error(f"Failed to archive message to S3: {error}")
            )

    # Step 7: [Messaging] Publish message to Pulsar topic
    # Message payload includes full context for downstream consumers
    pulsar_payload = (
        f"{message_id}|{user.user_id}|{user.email}|"
        f"{created_at.isoformat()}|{message.text}"
    ).encode("utf-8")

    publish_result = yield PublishMessage(topic="chat-messages", message=pulsar_payload)
    match publish_result:
        case Ok(_pulsar_message_id):
            pass
        case Err(error):
            return Err(
                AppError.internal_error(f"Failed to publish message to Pulsar: {error}")
            )

    # Step 8: [WebSocket] Broadcast message to connected clients (real-time)
    broadcast_result = yield BroadcastMessage(
        event="new_message",
        payload={
            "message_id": str(message.message_id),
            "user_id": str(user.user_id),
            "user_email": user.email,
            "user_name": user.name,
            "text": message.text,
            "created_at": created_at.isoformat(),
        },
    )
    match broadcast_result:
        case Ok(_):
            pass
        case Err(_error):
            # WebSocket broadcast failure is non-critical
            # Clients can poll or receive via Pulsar subscription
            pass

    # Step 9: Return successful response
    return Ok(
        MessageResponse(
            message_id=message.message_id,
            user_id=user.user_id,
            text=message.text,
            created_at=created_at,
        )
    )
