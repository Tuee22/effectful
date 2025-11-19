"""ChatMessage domain model.

This module defines the ChatMessage entity.
All domain models are immutable and use ADTs to eliminate Optional types.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ChatMessage:
    """Chat message entity.

    Represents a single message in a chat conversation.

    Attributes:
        id: Unique identifier for the message
        user_id: ID of the user who sent the message
        text: Content of the message
        created_at: Timestamp when message was created
    """

    id: UUID
    user_id: UUID
    text: str
    created_at: datetime
