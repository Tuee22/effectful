"""Authentication Helpers for E2E Tests.

Provides helpers for waiting on auth state transitions and
handling the Zustand auth store hydration.

Critical for WebKit which has slower localStorage access.

Usage:
    # After login, wait for auth to hydrate
    await wait_for_auth_hydration(page)

    # Check current auth state
    state = await get_auth_state(page)
    assert state["type"] == "Authenticated"
"""

from __future__ import annotations

from playwright.async_api import Page


async def wait_for_auth_hydration(
    page: Page,
    timeout_ms: int = 10000,
) -> None:
    """Wait for Zustand auth store to fully hydrate from localStorage.

    This is critical for WebKit which has slower localStorage access.
    Prevents race conditions where components load before auth is ready.

    The auth store uses 'healthhub-auth' key in localStorage with structure:
    {
        "state": {
            "authState": {
                "type": "Authenticated" | "Unauthenticated" | etc.
            }
        }
    }

    Args:
        page: Playwright page
        timeout_ms: Maximum wait time in milliseconds

    Raises:
        TimeoutError: If auth hydration doesn't complete in time
    """
    await page.evaluate(
        """
        async (timeoutMs) => {
            const startTime = Date.now();

            while (Date.now() - startTime < timeoutMs) {
                const authStorage = localStorage.getItem('healthhub-auth');

                if (authStorage) {
                    try {
                        const parsed = JSON.parse(authStorage);
                        const authState = parsed?.state?.authState;

                        if (authState?.type && authState.type !== 'Hydrating') {
                            console.log(`[Test Helper] Auth hydration complete: ${authState.type}`);
                            return true;
                        }
                    } catch (e) {
                        console.log('[Test Helper] Invalid auth storage JSON, waiting...');
                    }
                }

                await new Promise(resolve => setTimeout(resolve, 50));
            }

            throw new Error('Auth hydration timeout after ' + timeoutMs + 'ms');
        }
        """,
        timeout_ms,
    )


async def get_auth_state(page: Page) -> dict[str, object]:
    """Get the current auth state from localStorage.

    Returns:
        Dict with auth state, or empty dict if not found

    Example:
        state = await get_auth_state(page)
        assert state.get("type") == "Authenticated"
    """
    result = await page.evaluate(
        """
        () => {
            const authStorage = localStorage.getItem('healthhub-auth');
            if (!authStorage) return {};

            try {
                const parsed = JSON.parse(authStorage);
                return parsed?.state?.authState || {};
            } catch (e) {
                return {};
            }
        }
        """
    )
    return dict(result) if result else {}


async def is_authenticated(page: Page) -> bool:
    """Check if the user is currently authenticated.

    Returns:
        True if auth state type is "Authenticated"
    """
    state = await get_auth_state(page)
    return state.get("type") == "Authenticated"


async def get_current_user_email(page: Page) -> str | None:
    """Get the email of the currently authenticated user.

    Returns:
        Email string or None if not authenticated
    """
    state = await get_auth_state(page)
    if state.get("type") != "Authenticated":
        return None
    email = state.get("email")
    return email if isinstance(email, str) else None


async def get_current_user_role(page: Page) -> str | None:
    """Get the role of the currently authenticated user.

    Returns:
        Role string ("patient", "doctor", "admin") or None
    """
    state = await get_auth_state(page)
    if state.get("type") != "Authenticated":
        return None
    role = state.get("role")
    return role if isinstance(role, str) else None


async def clear_auth_state(page: Page) -> None:
    """Clear the auth state from localStorage.

    Useful for testing logout flows or resetting between tests.
    """
    await page.evaluate(
        """
        () => {
            localStorage.removeItem('healthhub-auth');
            sessionStorage.clear();
        }
        """
    )


# =============================================================================
# Test User Credentials (from seed_data.sql)
# =============================================================================

# All test users use the same password
TEST_PASSWORD = "password123"

# Test users by role
TEST_USERS = {
    "admin": {
        "email": "admin@healthhub.com",
        "password": TEST_PASSWORD,
    },
    "superadmin": {
        "email": "superadmin@healthhub.com",
        "password": TEST_PASSWORD,
    },
    "doctor": {
        "email": "dr.smith@healthhub.com",
        "password": TEST_PASSWORD,
    },
    "doctor2": {
        "email": "dr.johnson@healthhub.com",
        "password": TEST_PASSWORD,
    },
    "patient": {
        "email": "alice.patient@example.com",
        "password": TEST_PASSWORD,
    },
    "patient2": {
        "email": "bob.patient@example.com",
        "password": TEST_PASSWORD,
    },
}
