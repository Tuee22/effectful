# Tutorial 10: Auth Effects

This tutorial covers authentication effects for JWT token management and password operations.

## Overview

The auth effect system provides:
- JWT token validation, generation, and refresh
- Token revocation/blacklisting
- Password hashing and validation
- User lookup by email

All auth operations are type-safe with explicit result types.

## Auth Effects

### ValidateToken

Validates a JWT token and extracts user claims.

```python
from effectful import ValidateToken, TokenValid, TokenExpired, TokenInvalid

def authenticate_request(
    token: str
) -> Generator[AllEffects, EffectResult, UUID | None]:
    result = yield ValidateToken(token=token)

    match result:
        case TokenValid(user_id=uid, claims=claims):
            yield SendText(text=f"Authenticated user: {uid}")
            return uid
        case TokenExpired(expired_at=exp):
            yield SendText(text=f"Token expired at {exp}")
            return None
        case TokenInvalid(reason=reason):
            yield SendText(text=f"Invalid token: {reason}")
            return None
```

### GenerateToken

Creates a new JWT token for a user.

```python
from effectful import GenerateToken

def create_session(
    user_id: UUID,
    role: str
) -> Generator[AllEffects, EffectResult, str]:
    token = yield GenerateToken(
        user_id=user_id,
        claims={"role": role, "type": "access"},
        ttl_seconds=3600  # 1 hour
    )

    assert isinstance(token, str)
    yield SendText(text="Session created")
    return token
```

### RefreshToken

Exchanges a refresh token for a new access token.

```python
from effectful import RefreshToken

from effectful.domain.token_result import TokenRefreshed, TokenRefreshFailed

def refresh_session(
    refresh_token: str
) -> Generator[AllEffects, EffectResult, str | None]:
    result = yield RefreshToken(refresh_token=refresh_token)

    match result:
        case TokenRefreshFailed():
            yield SendText(text="Refresh token invalid or expired")
            return None
        case TokenRefreshed(access_token=new_token):
            yield SendText(text="Token refreshed")
            return new_token
```

### RevokeToken

Blacklists a token to prevent further use.

```python
from effectful import RevokeToken

def logout(
    token: str
) -> Generator[AllEffects, EffectResult, None]:
    yield RevokeToken(token=token)
    yield SendText(text="Logged out successfully")
    return None
```

### Password Operations

```python
from effectful import HashPassword, ValidatePassword, GetUserByEmail

def register_user(
    email: str,
    password: str
) -> Generator[AllEffects, EffectResult, bool]:
    # Hash password
    password_hash = yield HashPassword(password=password)
    assert isinstance(password_hash, str)

    # Save user with hashed password
    # (would use SaveUser effect in production)
    yield SendText(text=f"User {email} registered")
    return True


from effectful.domain.user import UserNotFound

def login(
    email: str,
    password: str
) -> Generator[AllEffects, EffectResult, str | None]:
    # Look up user
    user = yield GetUserByEmail(email=email)

    match user:
        case UserNotFound():
            yield SendText(text="User not found")
            return None
        case User():
            pass

    # Validate password (assuming user has password_hash field)
    # In production, you'd get the hash from the user record
    is_valid = yield ValidatePassword(
        password=password,
        password_hash=user.password_hash  # hypothetical field
    )

    if not is_valid:
        yield SendText(text="Invalid password")
        return None

    # Generate token
    token = yield GenerateToken(
        user_id=user.id,
        claims={"email": user.email},
        ttl_seconds=3600
    )

    assert isinstance(token, str)
    yield SendText(text="Login successful")
    return token
```

## Complete Authentication Flow

Here's a complete example combining multiple auth effects:

```python
from collections.abc import Generator
from uuid import UUID
from effectful import (
    AllEffects,
    EffectResult,
    ValidateToken,
    GenerateToken,
    RefreshToken,
    RevokeToken,
    GetUserByEmail,
    ValidatePassword,
    HashPassword,
    TokenValid,
    TokenExpired,
    TokenInvalid,
    User,
    SendText,
)


def authenticate_and_authorize(
    token: str,
    required_role: str
) -> Generator[AllEffects, EffectResult, bool]:
    """Validate token and check role-based authorization."""
    result = yield ValidateToken(token=token)

    match result:
        case TokenValid(user_id=uid, claims=claims):
            user_role = claims.get("role", "")
            if user_role == required_role:
                yield SendText(text=f"Authorized: {uid}")
                return True
            else:
                yield SendText(text=f"Forbidden: requires {required_role}")
                return False

        case TokenExpired():
            yield SendText(text="Token expired - please refresh")
            return False

        case TokenInvalid(reason=reason):
            yield SendText(text=f"Authentication failed: {reason}")
            return False


def protected_action(
    token: str
) -> Generator[AllEffects, EffectResult, str]:
    """Example protected endpoint requiring admin role."""

    # Check authorization
    authorized = yield from authenticate_and_authorize(token, "admin")

    if not authorized:
        return "Access denied"

    # Perform protected action
    yield SendText(text="Performing admin action...")
    return "Action completed"


def token_refresh_flow(
    access_token: str,
    refresh_token: str
) -> Generator[AllEffects, EffectResult, tuple[str, str] | None]:
    """Handle token refresh with validation."""

    # Check if access token is expired
    result = yield ValidateToken(token=access_token)

    match result:
        case TokenValid():
            # Token still valid, no refresh needed
            return (access_token, refresh_token)

        case TokenExpired():
            # Try to refresh
            refresh_result = yield RefreshToken(refresh_token=refresh_token)

            match refresh_result:
                case TokenRefreshFailed():
                    yield SendText(text="Session expired - please login again")
                    return None
                case TokenRefreshed(access_token=new_access):
                    pass

            # Generate new refresh token as well
            # (Extract user_id from old token claims for this example)
            new_refresh = yield GenerateToken(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                claims={"type": "refresh"},
                ttl_seconds=86400 * 7  # 7 days
            )

            assert isinstance(new_refresh, str)
            return (new_access, new_refresh)

        case TokenInvalid():
            yield SendText(text="Invalid token - please login again")
            return None
```

## Testing Auth Programs

Use the test interpreter to mock auth operations:

```python
import pytest
from pytest_mock import MockerFixture
from effectful import run_ws_program
from effectful.testing import unwrap_ok

@pytest.mark.asyncio
async def test_authentication(mocker: MockerFixture):
    # Create mock auth infrastructure
    mock_auth = mocker.AsyncMock(spec=AuthProtocol)
    mock_auth.validate_token.return_value = TokenValid(
        user_id=UUID("12345678-1234-1234-1234-123456789abc"),
        claims={"role": "admin"}
    )

    # Create interpreter with mocked infrastructure
    auth_interp = AuthInterpreter(auth_provider=mock_auth)
    interpreter = CompositeInterpreter(interpreters=[auth_interp])

    result = await run_ws_program(
        authenticate_and_authorize("valid-token", "admin"),
        interpreter
    )

    assert unwrap_ok(result) is True
```

## Best Practices

1. **Always handle all token states**: Use exhaustive pattern matching for `TokenValidationResult`

2. **Short-lived access tokens**: Use `ttl_seconds` of 15-60 minutes for access tokens

3. **Longer refresh tokens**: Refresh tokens can live for days/weeks

4. **Revoke on logout**: Always revoke tokens when users log out

5. **Hash passwords**: Never store plain text passwords

6. **Validate before authorization**: Always validate token before checking claims

## Error Handling

The `AuthInterpreter` may return `AuthError` for infrastructure failures:

```python
from effectful import AuthError

result = await run_ws_program(my_auth_program(), interpreter)

match result:
    case Ok(value):
        print(f"Success: {value}")
    case Err(AuthError(message=msg)):
        print(f"Auth error: {msg}")
```

## See Also

- [Auth API Reference](../api/auth.md) - Complete effect documentation
- [Effects Overview](../api/effects.md) - All effect types
- [Testing Guide](04_testing_guide.md) - Testing patterns
