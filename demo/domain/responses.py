"""Domain response types for demo app.

All responses are immutable ADTs using frozen dataclasses.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class LoginResponse:
    """Successful login response.

    Attributes:
        access_token: JWT access token
        refresh_token: JWT refresh token
        user_id: UUID of authenticated user
        expires_in: Seconds until access token expires
    """

    access_token: str
    refresh_token: str
    user_id: UUID
    expires_in: int


@dataclass(frozen=True)
class MessageResponse:
    """Message operation response.

    Attributes:
        message_id: UUID of the message
        user_id: UUID of the message author
        text: Message content
        created_at: Timestamp of message creation
    """

    message_id: UUID
    user_id: UUID
    text: str
    created_at: datetime
