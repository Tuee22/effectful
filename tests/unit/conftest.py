"""Pytest fixtures for unit testing.

Unit tests use pytest-mock only - no real infrastructure.
These fixtures provide common test data and mock helpers.
"""

from uuid import uuid4

import pytest


@pytest.fixture
def test_user_id() -> str:
    """Provide a unique user ID for testing.

    Returns:
        New UUID as string
    """
    return str(uuid4())
