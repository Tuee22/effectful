"""Integration tests for auth workflows with real Redis.

This module tests auth effect workflows using run_ws_program
with real Redis infrastructure. Each test uses auth_service fixture
which depends on clean_redis for declarative, idempotent test isolation.
"""

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.adapters.redis_auth import RedisAuthService
from effectful.algebraic.result import Err, Ok
from effectful.domain.token_result import (
    TokenExpired,
    TokenInvalid,
    TokenRefreshRejected,
    TokenRefreshed,
    TokenValid,
)
from effectful.domain.user import UserNotFound
from effectful.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RefreshToken,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)
from effectful.effects.websocket import SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestAuthWorkflowIntegration:
    """Integration tests for auth workflows with real Redis."""

    @pytest.mark.asyncio
    async def test_generate_and_validate_token_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Workflow generates token and validates it with real Redis."""
        user_id = uuid4()
        claims = {"role": "admin"}

        # Create interpreter with real auth
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define workflow
        def generate_validate_program(
            uid: UUID, user_claims: dict[str, str]
        ) -> Generator[AllEffects, EffectResult, str]:
            # Generate token
            token = yield GenerateToken(user_id=uid, claims=user_claims, ttl_seconds=3600)
            assert isinstance(token, str)

            yield SendText(text="Token generated")

            # Validate token
            validation = yield ValidateToken(token=token)

            match validation:
                case TokenValid(user_id=validated_uid, claims=validated_claims):
                    assert validated_uid == uid
                    yield SendText(text=f"Token valid for user {validated_uid}")
                    return "valid"
                case TokenExpired():
                    yield SendText(text="Token expired")
                    return "expired"
                case TokenInvalid(reason=reason):
                    yield SendText(text=f"Token invalid: {reason}")
                    return "invalid"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(generate_validate_program(user_id, claims), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "valid"
                assert mock_ws.send_text.call_count == 2
                mock_ws.send_text.assert_any_call("Token generated")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_revoke_token_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Workflow revokes token and verifies it's invalid."""
        user_id = uuid4()

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define workflow
        def revoke_token_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            # Generate token
            token = yield GenerateToken(user_id=uid, claims={}, ttl_seconds=3600)
            assert isinstance(token, str)

            # Verify it's valid
            validation1 = yield ValidateToken(token=token)
            match validation1:
                case TokenValid():
                    yield SendText(text="Token initially valid")
                case _:
                    return "error"

            # Revoke token
            yield RevokeToken(token=token)
            yield SendText(text="Token revoked")

            # Verify it's now invalid
            validation2 = yield ValidateToken(token=token)
            match validation2:
                case TokenInvalid(reason=reason):
                    yield SendText(text=f"Token now invalid: {reason}")
                    return "revoked"
                case _:
                    return "still_valid"

        # Act
        result = await run_ws_program(revoke_token_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "revoked"
                assert mock_ws.send_text.call_count == 3
                mock_ws.send_text.assert_any_call("Token initially valid")
                mock_ws.send_text.assert_any_call("Token revoked")
                mock_ws.send_text.assert_any_call("Token now invalid: revoked")
            case Err(error):
                pytest.fail(f"Expected Ok('revoked'), got Err({error})")

    @pytest.mark.asyncio
    async def test_refresh_token_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Workflow refreshes token to extend validity."""
        user_id = uuid4()
        claims = {"role": "user"}

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define workflow
        def refresh_token_program(
            uid: UUID, user_claims: dict[str, str]
        ) -> Generator[AllEffects, EffectResult, str]:
            # Generate initial token
            token = yield GenerateToken(user_id=uid, claims=user_claims, ttl_seconds=60)
            assert isinstance(token, str)

            # Refresh token
            refresh_result = yield RefreshToken(refresh_token=token)

            match refresh_result:
                case TokenRefreshed(access_token=new_access_token):
                    yield SendText(text="Token refreshed")

                    # Validate new token
                    validation = yield ValidateToken(token=new_access_token)
                    match validation:
                        case TokenValid(user_id=validated_uid):
                            assert validated_uid == uid
                            yield SendText(text="New token valid")
                            return "refreshed"
                        case _:
                            return "invalid"
                case TokenRefreshRejected():
                    yield SendText(text="Refresh failed")
                    return "failed"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(refresh_token_program(user_id, claims), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "refreshed"
                assert mock_ws.send_text.call_count == 2
                mock_ws.send_text.assert_any_call("Token refreshed")
                mock_ws.send_text.assert_any_call("New token valid")
            case Err(error):
                pytest.fail(f"Expected Ok('refreshed'), got Err({error})")

    @pytest.mark.asyncio
    async def test_validate_invalid_token_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Workflow handles invalid token gracefully."""
        invalid_token = "not.a.valid.jwt.token"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define workflow
        def validate_invalid_program(
            token: str,
        ) -> Generator[AllEffects, EffectResult, str]:
            validation = yield ValidateToken(token=token)

            match validation:
                case TokenValid():
                    return "valid"
                case TokenExpired():
                    yield SendText(text="Token expired")
                    return "expired"
                case TokenInvalid(reason=reason):
                    yield SendText(text=f"Token invalid: {reason}")
                    return "invalid"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(validate_invalid_program(invalid_token), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "invalid"
                mock_ws.send_text.assert_called_once()
                # Check that invalid reason is communicated
                call_args = mock_ws.send_text.call_args[0][0]
                assert "invalid" in call_args.lower()
            case Err(error):
                pytest.fail(f"Expected Ok('invalid'), got Err({error})")

    @pytest.mark.asyncio
    async def test_login_flow_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Complete login flow: generate, validate, use token."""
        user_id = uuid4()
        claims = {"role": "admin", "permissions": "read,write"}

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define complete login flow
        def login_flow_program(
            uid: UUID, user_claims: dict[str, str]
        ) -> Generator[AllEffects, EffectResult, bool]:
            # 1. Generate access token
            access_token = yield GenerateToken(user_id=uid, claims=user_claims, ttl_seconds=3600)
            assert isinstance(access_token, str)
            yield SendText(text="Access token generated")

            # 2. Validate token and extract user info
            validation = yield ValidateToken(token=access_token)

            match validation:
                case TokenValid(user_id=validated_uid, claims=validated_claims):
                    yield SendText(
                        text=f"Logged in as {validated_uid}, role: {validated_claims.get('role', 'unknown')}"
                    )
                case _:
                    yield SendText(text="Login failed")
                    return False

            # 3. Simulate logout - revoke token
            yield RevokeToken(token=access_token)
            yield SendText(text="Logged out successfully")

            return True

        # Act
        result = await run_ws_program(login_flow_program(user_id, claims), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert mock_ws.send_text.call_count == 3
                mock_ws.send_text.assert_any_call("Access token generated")
                mock_ws.send_text.assert_any_call("Logged out successfully")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_hash_password_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Workflow hashes password with PBKDF2-HMAC-SHA256."""
        password = "secure_password_123"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define workflow
        def hash_password_program(
            pwd: str,
        ) -> Generator[AllEffects, EffectResult, str]:
            password_hash = yield HashPassword(password=pwd)
            assert isinstance(password_hash, str)

            # Verify format: salt$hash
            parts = password_hash.split("$")
            if len(parts) == 2:
                yield SendText(text="Password hashed successfully")
                return password_hash
            else:
                yield SendText(text="Invalid hash format")
                return ""

        # Act
        result = await run_ws_program(hash_password_program(password), interpreter)

        # Assert
        match result:
            case Ok(password_hash):
                assert password_hash != ""
                parts = password_hash.split("$")
                assert len(parts) == 2
                # Salt should be 64 hex chars (32 bytes)
                assert len(parts[0]) == 64
                # Hash should be 64 hex chars (32 bytes from SHA256)
                assert len(parts[1]) == 64
                mock_ws.send_text.assert_called_once_with("Password hashed successfully")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_validate_password_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Workflow validates password against hash."""
        password = "my_secret_password"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define workflow
        def validate_password_program(
            pwd: str,
        ) -> Generator[AllEffects, EffectResult, bool]:
            # First hash the password
            password_hash = yield HashPassword(password=pwd)
            assert isinstance(password_hash, str)

            # Validate correct password
            is_valid = yield ValidatePassword(password=pwd, password_hash=password_hash)
            assert isinstance(is_valid, bool)

            if is_valid:
                yield SendText(text="Password validated")
                return True
            else:
                yield SendText(text="Password invalid")
                return False

        # Act
        result = await run_ws_program(validate_password_program(password), interpreter)

        # Assert
        match result:
            case Ok(is_valid):
                assert is_valid is True
                mock_ws.send_text.assert_called_once_with("Password validated")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_validate_wrong_password_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Workflow rejects wrong password."""
        correct_password = "correct_password"
        wrong_password = "wrong_password"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define workflow
        def validate_wrong_password_program(
            correct_pwd: str, wrong_pwd: str
        ) -> Generator[AllEffects, EffectResult, bool]:
            # Hash the correct password
            password_hash = yield HashPassword(password=correct_pwd)
            assert isinstance(password_hash, str)

            # Try to validate with wrong password
            is_valid = yield ValidatePassword(password=wrong_pwd, password_hash=password_hash)
            assert isinstance(is_valid, bool)

            if is_valid:
                yield SendText(text="Password valid (unexpected)")
                return True
            else:
                yield SendText(text="Password rejected")
                return False

        # Act
        result = await run_ws_program(
            validate_wrong_password_program(correct_password, wrong_password), interpreter
        )

        # Assert
        match result:
            case Ok(is_valid):
                assert is_valid is False
                mock_ws.send_text.assert_called_once_with("Password rejected")
            case Err(error):
                pytest.fail(f"Expected Ok(False), got Err({error})")

    @pytest.mark.asyncio
    async def test_get_user_by_email_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Workflow handles user lookup by email (stub returns NotFound)."""
        email = "test@example.com"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define workflow
        def get_user_by_email_program(
            user_email: str,
        ) -> Generator[AllEffects, EffectResult, str]:
            user_result = yield GetUserByEmail(email=user_email)

            match user_result:
                case UserNotFound(reason=reason):
                    yield SendText(text=f"User not found: {reason}")
                    return "not_found"
                case _:
                    yield SendText(text="User found")
                    return "found"

        # Act
        result = await run_ws_program(get_user_by_email_program(email), interpreter)

        # Assert - RedisAuthService stub always returns UserNotFound
        match result:
            case Ok(outcome):
                assert outcome == "not_found"
                mock_ws.send_text.assert_called_once()
                call_args = mock_ws.send_text.call_args[0][0]
                assert "not found" in call_args.lower()
            case Err(error):
                pytest.fail(f"Expected Ok('not_found'), got Err({error})")

    @pytest.mark.asyncio
    async def test_full_auth_workflow(
        self, auth_service: RedisAuthService, mocker: MockerFixture
    ) -> None:
        """Complete auth workflow: hash password, generate token, validate."""
        user_id = uuid4()
        password = "full_workflow_password"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=auth_service,
        )

        # Define complete auth workflow
        def full_auth_program(uid: UUID, pwd: str) -> Generator[AllEffects, EffectResult, bool]:
            # 1. Hash password
            password_hash = yield HashPassword(password=pwd)
            assert isinstance(password_hash, str)
            yield SendText(text="Password hashed")

            # 2. Validate password
            is_valid = yield ValidatePassword(password=pwd, password_hash=password_hash)
            assert isinstance(is_valid, bool)
            if not is_valid:
                yield SendText(text="Password validation failed")
                return False
            yield SendText(text="Password validated")

            # 3. Generate token
            token = yield GenerateToken(user_id=uid, claims={"role": "user"}, ttl_seconds=3600)
            assert isinstance(token, str)
            yield SendText(text="Token generated")

            # 4. Validate token
            validation = yield ValidateToken(token=token)
            match validation:
                case TokenValid(user_id=validated_uid):
                    assert validated_uid == uid
                    yield SendText(text="Token validated")
                    return True
                case _:
                    yield SendText(text="Token validation failed")
                    return False

        # Act
        result = await run_ws_program(full_auth_program(user_id, password), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert mock_ws.send_text.call_count == 4
                mock_ws.send_text.assert_any_call("Password hashed")
                mock_ws.send_text.assert_any_call("Password validated")
                mock_ws.send_text.assert_any_call("Token generated")
                mock_ws.send_text.assert_any_call("Token validated")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")
