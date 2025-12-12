# Auth Effects API Reference

**Status**: Authoritative source\
**Supersedes**: none\
**Referenced by**: documents/api/README.md

> **Purpose**: Reference for authentication effect types used for JWT token management and password operations.

## Effect Types

### ValidateToken

Validates a JWT token and extracts user claims.

```python
# file: examples/auth.py
@dataclass(frozen=True)
class ValidateToken:
    token: str
```

**Parameters:**

- `token` - The JWT token to validate

**Returns:** `TokenValidationResult` (see Domain Models below)

**Example:**

```python
# file: examples/auth.py
from effectful import ValidateToken, TokenValid, TokenExpired, TokenInvalid

def check_auth(
    token: str
) -> Generator[AllEffects, EffectResult, UUID | None]:
    result = yield ValidateToken(token=token)

    match result:
        case TokenValid(user_id=uid, claims=claims):
            return uid
        case TokenExpired(expired_at=exp):
            yield SendText(text=f"Token expired: {exp}")
            return None
        case TokenInvalid(reason=reason):
            yield SendText(text=f"Invalid: {reason}")
            return None
```

### GenerateToken

Generates a new JWT token for a user.

```python
# file: examples/auth.py
@dataclass(frozen=True)
class GenerateToken:
    user_id: UUID
    claims: dict[str, str]
    ttl_seconds: int
```

**Parameters:**

- `user_id` - UUID of the user to generate token for
- `claims` - Claims to include (roles, permissions, metadata)
- `ttl_seconds` - Token time-to-live in seconds

**Returns:** `str` (encoded JWT token)

**Example:**

```python
# file: examples/auth.py
from effectful import GenerateToken

def create_access_token(
    user_id: UUID,
    role: str
) -> Generator[AllEffects, EffectResult, str]:
    token = yield GenerateToken(
        user_id=user_id,
        claims={"role": role, "type": "access"},
        ttl_seconds=3600
    )

    assert isinstance(token, str)
    return token
```

### RefreshToken

Refreshes an existing token to extend validity.

```python
# file: examples/auth.py
@dataclass(frozen=True)
class RefreshToken:
    refresh_token: str
```

**Parameters:**

- `refresh_token` - The refresh token to exchange

**Returns:** `str | None` (new JWT token, or None if invalid/expired)

**Example:**

```python
# file: examples/auth.py
from effectful import RefreshToken

def refresh_access(
    refresh_token: str
) -> Generator[AllEffects, EffectResult, str | None]:
    new_token = yield RefreshToken(refresh_token=refresh_token)

    if new_token is None:
        return None

    assert isinstance(new_token, str)
    return new_token
```

### RevokeToken

Revokes/blacklists a token to prevent further use.

```python
# file: examples/auth.py
@dataclass(frozen=True)
class RevokeToken:
    token: str
```

**Parameters:**

- `token` - The JWT token to revoke

**Returns:** `None`

**Example:**

```python
# file: examples/auth.py
from effectful import RevokeToken

def logout(token: str) -> Generator[AllEffects, EffectResult, None]:
    yield RevokeToken(token=token)
    yield SendText(text="Logged out")
    return None
```

### GetUserByEmail

Gets a user by email address.

```python
# file: examples/auth.py
@dataclass(frozen=True)
class GetUserByEmail:
    email: str
```

**Parameters:**

- `email` - Email address to search for

**Returns:** `User | None`

**Example:**

```python
# file: examples/auth.py
from effectful import GetUserByEmail, User

def find_user(
    email: str
) -> Generator[AllEffects, EffectResult, User | None]:
    user = yield GetUserByEmail(email=email)

    if user is None:
        return None

    assert isinstance(user, User)
    return user
```

### ValidatePassword

Validates a password against a bcrypt hash.

```python
# file: examples/auth.py
@dataclass(frozen=True)
class ValidatePassword:
    password: str
    password_hash: str
```

**Parameters:**

- `password` - Plain text password to validate
- `password_hash` - Bcrypt hash to validate against

**Returns:** `bool`

**Example:**

```python
# file: examples/auth.py
from effectful import ValidatePassword

def check_password(
    password: str,
    stored_hash: str
) -> Generator[AllEffects, EffectResult, bool]:
    is_valid = yield ValidatePassword(
        password=password,
        password_hash=stored_hash
    )

    return is_valid
```

### HashPassword

Hashes a password with bcrypt.

```python
# file: examples/auth.py
@dataclass(frozen=True)
class HashPassword:
    password: str
```

**Parameters:**

- `password` - Plain text password to hash

**Returns:** `str` (bcrypt hash)

**Example:**

```python
# file: examples/auth.py
from effectful import HashPassword

def hash_new_password(
    password: str
) -> Generator[AllEffects, EffectResult, str]:
    hashed = yield HashPassword(password=password)

    assert isinstance(hashed, str)
    return hashed
```

## Domain Models

### TokenValidationResult

ADT for token validation outcomes.

```python
# file: examples/auth.py
type TokenValidationResult = TokenValid | TokenExpired | TokenInvalid

@dataclass(frozen=True)
class TokenValid:
    user_id: UUID
    claims: dict[str, str]

@dataclass(frozen=True)
class TokenExpired:
    token: str
    expired_at: datetime

@dataclass(frozen=True)
class TokenInvalid:
    token: str
    reason: str
```

**Pattern Matching:**

```python
# file: examples/auth.py
result = yield ValidateToken(token=token)

match result:
    case TokenValid(user_id=uid, claims=claims):
        # Token is valid - uid is authenticated user
        pass
    case TokenExpired(token=t, expired_at=exp):
        # Token has expired - suggest refresh
        pass
    case TokenInvalid(token=t, reason=reason):
        # Token is invalid (malformed, revoked, bad signature)
        pass
```

**Reason Values for TokenInvalid:**

- `"revoked"` - Token was explicitly revoked
- `"invalid_signature"` - Signature verification failed
- `"malformed"` - Token structure is invalid

## Error Handling

The `AuthInterpreter` may return `AuthError` for infrastructure failures:

```python
# file: examples/auth.py
from effectful import AuthError

result = await run_ws_program(my_program(), interpreter)

match result:
    case Ok(value):
        print(f"Success: {value}")
    case Err(AuthError(message=msg)):
        print(f"Auth error: {msg}")
    case Err(error):
        print(f"Other error: {error}")
```

## Complete Workflow Example

```python
# file: examples/auth.py
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


def login_flow(
    email: str,
    password: str
) -> Generator[AllEffects, EffectResult, tuple[str, str] | None]:
    """Complete login flow returning access and refresh tokens."""

    # Find user by email
    user = yield GetUserByEmail(email=email)
    if user is None:
        yield SendText(text="User not found")
        return None

    assert isinstance(user, User)

    # Validate password (assuming user model has password_hash)
    # Note: In real app, you'd store hash in user model
    is_valid = yield ValidatePassword(
        password=password,
        password_hash="$2b$12$..."  # Retrieved from user record
    )

    if not is_valid:
        yield SendText(text="Invalid password")
        return None

    # Generate access token
    access_token = yield GenerateToken(
        user_id=user.id,
        claims={"email": user.email, "type": "access"},
        ttl_seconds=3600  # 1 hour
    )

    # Generate refresh token
    refresh_token = yield GenerateToken(
        user_id=user.id,
        claims={"type": "refresh"},
        ttl_seconds=604800  # 7 days
    )

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)

    yield SendText(text="Login successful")
    return (access_token, refresh_token)


def protected_endpoint(
    token: str,
    required_role: str
) -> Generator[AllEffects, EffectResult, dict[str, str]]:
    """Protected endpoint with role-based authorization."""

    # Validate token
    result = yield ValidateToken(token=token)

    match result:
        case TokenValid(user_id=uid, claims=claims):
            # Check role
            user_role = claims.get("role", "")
            if user_role != required_role:
                yield SendText(text=f"Forbidden: requires {required_role}")
                return {"error": "forbidden"}

            # Perform action
            return {"user_id": str(uid), "status": "success"}

        case TokenExpired():
            yield SendText(text="Token expired")
            return {"error": "expired"}

        case TokenInvalid(reason=reason):
            yield SendText(text=f"Unauthorized: {reason}")
            return {"error": "unauthorized"}


def logout_flow(
    access_token: str,
    refresh_token: str
) -> Generator[AllEffects, EffectResult, None]:
    """Logout by revoking both tokens."""

    yield RevokeToken(token=access_token)
    yield RevokeToken(token=refresh_token)
    yield SendText(text="Logged out - both tokens revoked")
    return None
```

## See Also

- [Effects Overview](effects.md) - All effect types
- [Tutorial: Auth Effects](../tutorials/auth_effects.md) - Step-by-step guide
- [Interpreters](interpreters.md) - AuthInterpreter details
- [Testing Guide](../tutorials/testing_guide.md) - Testing auth programs

______________________________________________________________________

## Cross-References

- [Documentation Standards](../documentation_standards.md)
- [Engineering Architecture](../engineering/architecture.md)
