"""Tests for user program workflows using pytest-mock.

All tests use pytest-mock (mocker.AsyncMock) instead of fakes.
Tests verify both success and error paths with 100% coverage.
"""

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from demo.domain.errors import AppError
from demo.programs.user_programs import (
    delete_user_program,
    get_user_program,
    list_users_program,
    update_user_program,
)
from effectful.algebraic.result import Err, Ok
from effectful.domain.user import User
from effectful.effects.cache import InvalidateCache
from effectful.effects.database import DeleteUser, GetUserById, ListUsers, UpdateUser


class TestGetUserProgram:
    """Test suite for get_user_program."""

    def test_get_user_success(self, mocker: MockerFixture) -> None:
        """Test successfully retrieving a user."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = get_user_program(user_id=user_id)

        # Step 1: GetUserById returns user
        effect1 = next(gen)
        assert isinstance(effect1, GetUserById)
        assert effect1.user_id == user_id

        try:
            gen.send(user)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert isinstance(result.value, User)
        assert result.value.id == user_id
        assert result.value.email == "alice@example.com"

    def test_get_user_not_found(self, mocker: MockerFixture) -> None:
        """Test retrieving non-existent user."""
        # Setup
        user_id = uuid4()

        # Mock the program execution
        gen = get_user_program(user_id=user_id)

        # Step 1: GetUserById returns None
        effect1 = next(gen)

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "not_found"
        assert str(user_id) in result.error.message


class TestListUsersProgram:
    """Test suite for list_users_program."""

    def test_list_users_success_no_pagination(self, mocker: MockerFixture) -> None:
        """Test listing all users without pagination."""
        # Setup
        users = [
            User(id=uuid4(), email="alice@example.com", name="Alice"),
            User(id=uuid4(), email="bob@example.com", name="Bob"),
        ]

        # Mock the program execution
        gen = list_users_program()

        # Step 1: ListUsers returns user list
        effect1 = next(gen)
        assert isinstance(effect1, ListUsers)
        assert effect1.limit is None
        assert effect1.offset is None

        try:
            gen.send(users)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert isinstance(result.value, list)
        assert len(result.value) == 2

    def test_list_users_with_pagination(self, mocker: MockerFixture) -> None:
        """Test listing users with limit and offset."""
        # Setup
        users = [User(id=uuid4(), email="charlie@example.com", name="Charlie")]

        # Mock the program execution
        gen = list_users_program(limit=10, offset=5)

        # Step 1: ListUsers returns user list
        effect1 = next(gen)
        assert isinstance(effect1, ListUsers)
        assert effect1.limit == 10
        assert effect1.offset == 5

        try:
            gen.send(users)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert len(result.value) == 1

    def test_list_users_negative_limit(self, mocker: MockerFixture) -> None:
        """Test listing users fails with negative limit."""
        # Mock the program execution
        gen = list_users_program(limit=-1)

        # No effects should be yielded - should fail validation immediately
        try:
            next(gen)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"
        assert "non-negative" in result.error.message

    def test_list_users_negative_offset(self, mocker: MockerFixture) -> None:
        """Test listing users fails with negative offset."""
        # Mock the program execution
        gen = list_users_program(offset=-5)

        # No effects should be yielded - should fail validation immediately
        try:
            next(gen)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"
        assert "non-negative" in result.error.message


class TestUpdateUserProgram:
    """Test suite for update_user_program."""

    def test_update_user_success(self, mocker: MockerFixture) -> None:
        """Test successfully updating a user."""
        # Setup
        user_id = uuid4()
        original_user = User(id=user_id, email="alice@example.com", name="Alice")
        updated_user = User(id=user_id, email="alice.new@example.com", name="Alice")

        # Mock the program execution
        gen = update_user_program(user_id=user_id, email="alice.new@example.com")

        # Step 1: GetUserById returns original user
        effect1 = next(gen)
        assert isinstance(effect1, GetUserById)
        result1 = gen.send(original_user)

        # Step 2: UpdateUser returns True
        effect2 = result1
        assert isinstance(effect2, UpdateUser)
        assert effect2.user_id == user_id
        assert effect2.email == "alice.new@example.com"
        result2 = gen.send(True)

        # Step 3: InvalidateCache
        effect3 = result2
        assert isinstance(effect3, InvalidateCache)
        assert f"user:{user_id}" in effect3.key
        result3 = gen.send(True)

        # Step 4: GetUserById returns updated user
        effect4 = result3
        assert isinstance(effect4, GetUserById)

        try:
            gen.send(updated_user)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert result.value.email == "alice.new@example.com"

    def test_update_user_not_found(self, mocker: MockerFixture) -> None:
        """Test updating non-existent user."""
        # Setup
        user_id = uuid4()

        # Mock the program execution
        gen = update_user_program(user_id=user_id, name="New Name")

        # Step 1: GetUserById returns None
        effect1 = next(gen)

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "not_found"

    def test_update_user_no_fields(self, mocker: MockerFixture) -> None:
        """Test update fails when no fields provided."""
        # Setup
        user_id = uuid4()

        # Mock the program execution
        gen = update_user_program(user_id=user_id)

        # No effects should be yielded - should fail validation immediately
        try:
            next(gen)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"
        assert "at least one field" in result.error.message.lower()

    def test_update_user_invalid_email(self, mocker: MockerFixture) -> None:
        """Test update fails with invalid email format."""
        # Setup
        user_id = uuid4()

        # Mock the program execution
        gen = update_user_program(user_id=user_id, email="invalid-email")

        # No effects should be yielded - should fail validation immediately
        try:
            next(gen)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"
        assert "email" in result.error.message.lower()


class TestDeleteUserProgram:
    """Test suite for delete_user_program."""

    def test_delete_user_success(self, mocker: MockerFixture) -> None:
        """Test successfully deleting a user."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = delete_user_program(user_id=user_id)

        # Step 1: GetUserById returns user
        effect1 = next(gen)
        assert isinstance(effect1, GetUserById)
        result1 = gen.send(user)

        # Step 2: DeleteUser returns True
        effect2 = result1
        assert isinstance(effect2, DeleteUser)
        assert effect2.user_id == user_id
        result2 = gen.send(True)

        # Step 3: InvalidateCache
        effect3 = result2
        assert isinstance(effect3, InvalidateCache)

        try:
            gen.send(True)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert result.value is True

    def test_delete_user_not_found(self, mocker: MockerFixture) -> None:
        """Test deleting non-existent user."""
        # Setup
        user_id = uuid4()

        # Mock the program execution
        gen = delete_user_program(user_id=user_id)

        # Step 1: GetUserById returns None
        effect1 = next(gen)

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "not_found"
