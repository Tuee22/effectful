"""WebSocket effect DSL.

This module defines effects for WebSocket operations:
- SendText: Send text message to client
- ReceiveText: Wait for text message from client
- Close: Close the WebSocket connection with typed reason

All effects are immutable (frozen dataclasses).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SendText:
    """Effect: Send text message to WebSocket client.

    Attributes:
        text: The message to send
    """

    text: str


@dataclass(frozen=True)
class ReceiveText:
    """Effect: Receive text message from WebSocket client.

    This effect blocks until a message is received.
    """


# Close reason ADT - makes illegal states unrepresentable


@dataclass(frozen=True)
class CloseNormal:
    """Normal WebSocket closure (code 1000).

    Used when the connection completed its purpose successfully.
    """


@dataclass(frozen=True)
class CloseGoingAway:
    """Endpoint is going away (code 1001).

    Used when server is shutting down or client is navigating away.
    """


@dataclass(frozen=True)
class CloseProtocolError:
    """Protocol error occurred (code 1002).

    Attributes:
        reason: Description of the protocol error (required)
    """

    reason: str


@dataclass(frozen=True)
class ClosePolicyViolation:
    """Policy violation occurred (code 1008).

    Attributes:
        reason: Description of the policy violation (required)
    """

    reason: str


# ADT: Union of all close reasons using PEP 695 type statement
type CloseReason = CloseNormal | CloseGoingAway | CloseProtocolError | ClosePolicyViolation


@dataclass(frozen=True)
class Close:
    """Effect: Close WebSocket connection with typed reason.

    Using CloseReason ADT ensures:
    - Invalid close codes are impossible
    - Reasons are required when needed (protocol errors, policy violations)
    - Type system enforces correct usage

    Attributes:
        reason: The reason for closing (CloseReason ADT)
    """

    reason: CloseReason


# ADT: Union of all WebSocket effects using PEP 695 type statement
type WebSocketEffect = SendText | ReceiveText | Close
