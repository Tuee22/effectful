"""JWT token generation and validation with dual-token pattern.

Access Token: 15 minutes (short-lived)
Refresh Token: 7 days (long-lived, stored in HttpOnly cookie)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal
from uuid import UUID

import jwt

from app.config import Settings
from effectful.domain.optional_value import OptionalValue, to_optional_value


class TokenType(str, Enum):
    """Token type enumeration."""

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class TokenData:
    """Decoded JWT token data with profile IDs for performance optimization."""

    user_id: UUID
    email: str
    role: str
    token_type: TokenType
    patient_id: OptionalValue[UUID]  # NEW: Eliminates DB lookup for patient authorization
    doctor_id: OptionalValue[UUID]  # NEW: Eliminates DB lookup for doctor authorization
    exp: datetime
    iat: datetime


@dataclass(frozen=True)
class TokenValidationSuccess:
    """Successful token validation result."""

    token_data: TokenData


@dataclass(frozen=True)
class TokenValidationError:
    """Failed token validation result."""

    reason: Literal["expired", "invalid", "malformed"]
    detail: str


type TokenValidationResult = TokenValidationSuccess | TokenValidationError


def create_access_token(
    settings: Settings,
    user_id: UUID,
    email: str,
    role: str,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
) -> str:
    """Create a short-lived JWT access token (15 minutes) with profile IDs.

    Args:
        settings: Application settings for JWT configuration
        user_id: User UUID
        email: User email
        role: User role (patient, doctor, admin)
        patient_id: Patient profile UUID (if role is patient)
        doctor_id: Doctor profile UUID (if role is doctor)

    Returns:
        Encoded JWT access token with profile IDs for performance optimization
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expire = now + expires_delta

    payload = {
        "user_id": str(user_id),
        "email": email,
        "role": role,
        "token_type": TokenType.ACCESS.value,
        "patient_id": str(patient_id) if patient_id else None,
        "doctor_id": str(doctor_id) if doctor_id else None,
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    settings: Settings,
    user_id: UUID,
    email: str,
    role: str,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
) -> str:
    """Create a long-lived JWT refresh token (7 days) with profile IDs.

    Args:
        settings: Application settings for JWT configuration
        user_id: User UUID
        email: User email
        role: User role (patient, doctor, admin)
        patient_id: Patient profile UUID (if role is patient)
        doctor_id: Doctor profile UUID (if role is doctor)

    Returns:
        Encoded JWT refresh token with profile IDs for performance optimization
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)
    expire = now + expires_delta

    payload = {
        "user_id": str(user_id),
        "email": email,
        "role": role,
        "token_type": TokenType.REFRESH.value,
        "patient_id": str(patient_id) if patient_id else None,
        "doctor_id": str(doctor_id) if doctor_id else None,
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(settings: Settings, token: str, expected_type: TokenType) -> TokenValidationResult:
    """Verify and decode a JWT token.

    Args:
        settings: Application settings for JWT configuration
        token: JWT token string
        expected_type: Expected token type (access or refresh)

    Returns:
        TokenValidationSuccess with token data, or TokenValidationError
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        token_type = payload.get("token_type")
        if token_type != expected_type.value:
            return TokenValidationError(
                reason="invalid",
                detail=f"Expected {expected_type.value} token, got {token_type}",
            )

        patient_id_value = UUID(payload["patient_id"]) if payload.get("patient_id") else None
        doctor_id_value = UUID(payload["doctor_id"]) if payload.get("doctor_id") else None

        token_data = TokenData(
            user_id=UUID(payload["user_id"]),
            email=payload["email"],
            role=payload["role"],
            token_type=TokenType(token_type),
            patient_id=to_optional_value(patient_id_value, reason="not_included"),
            doctor_id=to_optional_value(doctor_id_value, reason="not_included"),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )

        return TokenValidationSuccess(token_data=token_data)

    except jwt.ExpiredSignatureError:
        return TokenValidationError(
            reason="expired",
            detail="Token has expired",
        )
    except (jwt.InvalidTokenError, jwt.DecodeError):
        return TokenValidationError(
            reason="invalid",
            detail="Invalid token signature",
        )
    except (ValueError, KeyError) as e:
        return TokenValidationError(
            reason="malformed",
            detail=f"Malformed token payload: {e}",
        )
