"""Tests for Auth effects.

Tests cover:
- Immutability (frozen dataclasses)
- Construction of each effect variant
- Type safety with UUID and dict types
"""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from effectful.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RefreshToken,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)


class TestValidateToken:
    """Test ValidateToken effect."""

    def test_validate_token_creates_effect(self) -> None:
        """ValidateToken should wrap token string."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        effect = ValidateToken(token=token)
        assert effect.token == token

    def test_validate_token_is_immutable(self) -> None:
        """ValidateToken should be frozen (immutable)."""
        effect = ValidateToken(token="test.token")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "token", "new.token")

    def test_validate_token_equality(self) -> None:
        """ValidateToken should support equality comparison."""
        token = "test.token"
        effect1 = ValidateToken(token=token)
        effect2 = ValidateToken(token=token)
        assert effect1 == effect2

    def test_validate_token_inequality(self) -> None:
        """ValidateToken with different tokens should not be equal."""
        effect1 = ValidateToken(token="token1")
        effect2 = ValidateToken(token="token2")
        assert effect1 != effect2


class TestGenerateToken:
    """Test GenerateToken effect."""

    def test_generate_token_creates_effect(self) -> None:
        """GenerateToken should wrap user_id, claims, and ttl_seconds."""
        user_id = uuid4()
        claims = {"role": "admin", "department": "engineering"}
        ttl = 3600
        effect = GenerateToken(user_id=user_id, claims=claims, ttl_seconds=ttl)
        assert effect.user_id == user_id
        assert effect.claims == claims
        assert effect.ttl_seconds == ttl

    def test_generate_token_is_immutable(self) -> None:
        """GenerateToken should be frozen (immutable)."""
        user_id = uuid4()
        claims = {"role": "user"}
        effect = GenerateToken(user_id=user_id, claims=claims, ttl_seconds=3600)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "ttl_seconds", 7200)

    def test_generate_token_user_id_is_immutable(self) -> None:
        """GenerateToken user_id should be immutable."""
        user_id = uuid4()
        effect = GenerateToken(user_id=user_id, claims={}, ttl_seconds=3600)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "user_id", uuid4())

    def test_generate_token_claims_is_immutable(self) -> None:
        """GenerateToken claims should be immutable."""
        user_id = uuid4()
        effect = GenerateToken(user_id=user_id, claims={}, ttl_seconds=3600)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "claims", {"new": "claims"})

    def test_generate_token_equality(self) -> None:
        """GenerateToken should support equality comparison."""
        user_id = uuid4()
        claims = {"role": "admin"}
        effect1 = GenerateToken(user_id=user_id, claims=claims, ttl_seconds=3600)
        effect2 = GenerateToken(user_id=user_id, claims=claims, ttl_seconds=3600)
        assert effect1 == effect2


class TestRefreshToken:
    """Test RefreshToken effect."""

    def test_refresh_token_creates_effect(self) -> None:
        """RefreshToken should wrap refresh_token string."""
        refresh = "refresh.token.value"
        effect = RefreshToken(refresh_token=refresh)
        assert effect.refresh_token == refresh

    def test_refresh_token_is_immutable(self) -> None:
        """RefreshToken should be frozen (immutable)."""
        effect = RefreshToken(refresh_token="test.refresh")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "refresh_token", "new.refresh")

    def test_refresh_token_equality(self) -> None:
        """RefreshToken should support equality comparison."""
        refresh = "refresh.token"
        effect1 = RefreshToken(refresh_token=refresh)
        effect2 = RefreshToken(refresh_token=refresh)
        assert effect1 == effect2


class TestRevokeToken:
    """Test RevokeToken effect."""

    def test_revoke_token_creates_effect(self) -> None:
        """RevokeToken should wrap token string."""
        token = "token.to.revoke"
        effect = RevokeToken(token=token)
        assert effect.token == token

    def test_revoke_token_is_immutable(self) -> None:
        """RevokeToken should be frozen (immutable)."""
        effect = RevokeToken(token="test.token")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "token", "new.token")

    def test_revoke_token_equality(self) -> None:
        """RevokeToken should support equality comparison."""
        token = "revoke.token"
        effect1 = RevokeToken(token=token)
        effect2 = RevokeToken(token=token)
        assert effect1 == effect2


class TestGetUserByEmail:
    """Test GetUserByEmail effect."""

    def test_get_user_by_email_creates_effect(self) -> None:
        """GetUserByEmail should wrap email string."""
        email = "user@example.com"
        effect = GetUserByEmail(email=email)
        assert effect.email == email

    def test_get_user_by_email_is_immutable(self) -> None:
        """GetUserByEmail should be frozen (immutable)."""
        effect = GetUserByEmail(email="test@example.com")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "email", "new@example.com")

    def test_get_user_by_email_equality(self) -> None:
        """GetUserByEmail should support equality comparison."""
        email = "user@example.com"
        effect1 = GetUserByEmail(email=email)
        effect2 = GetUserByEmail(email=email)
        assert effect1 == effect2


class TestValidatePassword:
    """Test ValidatePassword effect."""

    def test_validate_password_creates_effect(self) -> None:
        """ValidatePassword should wrap password and password_hash."""
        password = "secret123"
        password_hash = "$2b$12$..."
        effect = ValidatePassword(password=password, password_hash=password_hash)
        assert effect.password == password
        assert effect.password_hash == password_hash

    def test_validate_password_is_immutable(self) -> None:
        """ValidatePassword should be frozen (immutable)."""
        effect = ValidatePassword(password="secret", password_hash="hash")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "password", "newsecret")

    def test_validate_password_hash_is_immutable(self) -> None:
        """ValidatePassword password_hash should be immutable."""
        effect = ValidatePassword(password="secret", password_hash="hash")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "password_hash", "newhash")

    def test_validate_password_equality(self) -> None:
        """ValidatePassword should support equality comparison."""
        effect1 = ValidatePassword(password="secret", password_hash="hash")
        effect2 = ValidatePassword(password="secret", password_hash="hash")
        assert effect1 == effect2


class TestHashPassword:
    """Test HashPassword effect."""

    def test_hash_password_creates_effect(self) -> None:
        """HashPassword should wrap password string."""
        password = "secret123"
        effect = HashPassword(password=password)
        assert effect.password == password

    def test_hash_password_is_immutable(self) -> None:
        """HashPassword should be frozen (immutable)."""
        effect = HashPassword(password="secret")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "password", "newsecret")

    def test_hash_password_equality(self) -> None:
        """HashPassword should support equality comparison."""
        password = "secret123"
        effect1 = HashPassword(password=password)
        effect2 = HashPassword(password=password)
        assert effect1 == effect2
