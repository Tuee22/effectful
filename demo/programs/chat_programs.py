"""Complex chat workflow effect program demonstrating all 6 infrastructure types.

This module shows how to compose multiple effects across different infrastructure
layers into a single cohesive business workflow.
"""

from collections.abc import Generator
from datetime import datetime
from uuid import UUID, uuid4

from effectful.algebraic.result import Err, Ok, Result
from effectful.effects.auth import ValidateToken
from effectful.effects.cache import GetCachedValue, PutCachedValue
from effectful.effects.database import GetUserById
from effectful.effects.messaging import PublishMessage
from effectful.effects.storage import PutObject
from effectful.effects.websocket import SendText
from effectful.domain.s3_object import PutSuccess
from effectful.domain.token_result import TokenValid
from effectful.domain.user import User
from effectful.programs.program_types import AllEffects, EffectResult

from demo.domain.errors import AppError, AuthError
from demo.domain.responses import MessageResponse


def send_authenticated_message_with_storage_program(
    token: str, text: str
) -> Generator[AllEffects, EffectResult, Result[MessageResponse, AuthError | AppError]]:
    """Send authenticated message with S3 archival (all 6 infrastructure types).

    This program demonstrates a complete workflow using all infrastructure:
    - Auth: JWT token validation (ValidateToken)
    - Cache: User data cache-aside pattern with Redis (GetCachedValue, PutCachedValue)
    - Database: User lookup in PostgreSQL (GetUserById)
    - Storage: Message archival to S3 (PutObject)
    - Messaging: Publish to Pulsar topic (PublishMessage)
    - WebSocket: Real-time notification to client (SendText)

    Program flow:
    1. [Auth] Validate JWT token
    2. [Cache] Check for cached user data
    3. [Database] Load user from PostgreSQL (if cache miss)
    4. [Cache] Store user in cache for future requests
    5. [Storage] Archive message to S3 for compliance/audit
    6. [Messaging] Publish message to Pulsar topic
    7. [WebSocket] Send confirmation to client via WebSocket
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
        - S3 storage failure (PutObject returns PutSuccess, won't fail in demo)
        - Pulsar publish failure (returns string message ID, won't fail in demo)
    """
    # Step 1: [Auth] Validate JWT token
    validation_result = yield ValidateToken(token=token)

    if not isinstance(validation_result, TokenValid):
        return Err(
            AuthError(
                message="Invalid or expired token", error_type="token_invalid"
            )
        )

    user_id = validation_result.user_id

    # Step 2: [Cache] Check for cached user data (cache-aside pattern)
    cache_key = f"user:{user_id}"
    cached_result = yield GetCachedValue(key=cache_key)

    # For demo purposes, we always fetch from DB to show the pattern
    # In production, you would deserialize cached_result if it's not None

    # Step 3: [Database] Load user from PostgreSQL
    user = yield GetUserById(user_id=user_id)

    if user is None:
        return Err(AppError.not_found(f"User {user_id} not found"))

    assert isinstance(user, User)

    # Step 4: [Cache] Store user in Redis for future requests (TTL: 5 minutes)
    # In production, serialize User to bytes (JSON, msgpack, etc.)
    user_cache_bytes = f"{user.email}|{user.name}".encode("utf-8")
    yield PutCachedValue(key=cache_key, value=user_cache_bytes, ttl_seconds=300)

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

    # Step 6: [Storage] Archive message to S3 for compliance/audit
    # Object key: messages/{year}/{month}/{day}/{message_id}.txt
    s3_key = (
        f"messages/{created_at.year}/{created_at.month:02d}/"
        f"{created_at.day:02d}/{message_id}.txt"
    )
    s3_content = (
        f"Message ID: {message_id}\n"
        f"User ID: {user.id}\n"
        f"User Email: {user.email}\n"
        f"Created At: {created_at.isoformat()}\n\n"
        f"{text.strip()}"
    ).encode("utf-8")

    storage_result = yield PutObject(bucket="chat-archive", key=s3_key, content=s3_content)

    # In demo, PutObject may return PutSuccess or PutFailure
    # For simplicity, we proceed regardless (non-critical archival)
    if isinstance(storage_result, PutSuccess):
        # Successfully archived
        pass

    # Step 7: [Messaging] Publish message to Pulsar topic
    # Message payload includes full context for downstream consumers
    pulsar_payload = (
        f"{message_id}|{user.id}|{user.email}|"
        f"{created_at.isoformat()}|{text.strip()}"
    ).encode("utf-8")

    pulsar_message_id = yield PublishMessage(
        topic="chat-messages", payload=pulsar_payload
    )
    assert isinstance(pulsar_message_id, str)

    # Step 8: [WebSocket] Send confirmation to client via WebSocket
    yield SendText(text=f"Message sent: {message_id}")

    # Step 9: Return successful response
    return Ok(
        MessageResponse(
            message_id=message_id,
            user_id=user.id,
            text=text.strip(),
            created_at=created_at,
        )
    )
