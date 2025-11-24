"""E2E test fixtures.

Provides fixtures specific to E2E testing including:
- WebSocket client
- Composite interpreters with real infrastructure
"""

import pytest

from tests.e2e.client.ws_client import E2EWebSocketClient


@pytest.fixture
def ws_client() -> E2EWebSocketClient:
    """Provide a WebSocket test client for E2E tests.

    Returns:
        E2EWebSocketClient instance
    """
    return E2EWebSocketClient.create()
