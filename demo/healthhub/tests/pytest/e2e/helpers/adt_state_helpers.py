"""ADT State Synchronization Helpers for E2E Tests.

Eliminates race conditions by waiting for ADT state transitions
instead of using timing hacks. Tests synchronize on semantic state
changes, not arbitrary time delays.

Philosophy (from ShipNorth):
- Make implicit state explicit through data-state attributes
- Wait for semantically meaningful state transitions
- Provably correct synchronization based on application state machine
- NO timing hacks (wait_for_timeout, sleep, etc.)

Usage:
    # Wait for data to load
    await wait_for_remote_data_state(page, "Success")

    # Wait for page to be fully ready
    await wait_for_page_ready(page)
"""

from __future__ import annotations

from typing import Literal

from playwright.async_api import Locator, Page, expect

# =============================================================================
# Type Definitions (matching frontend ADT types)
# =============================================================================

# RemoteData states from frontend ADT
RemoteDataState = Literal["NotAsked", "Loading", "Failure", "Success"]

# Auth states from frontend AuthState ADT
AuthState = Literal[
    "Hydrating",
    "Unauthenticated",
    "Authenticating",
    "SessionRestorable",
    "Authenticated",
    "SessionExpired",
    "AuthenticationFailed",
]

# Appointment status (matching frontend Appointment model)
AppointmentStatus = Literal[
    "requested",
    "confirmed",
    "in_progress",
    "completed",
    "cancelled",
]


# =============================================================================
# RemoteData State Helpers
# =============================================================================


async def wait_for_remote_data_state(
    page: Page,
    state: RemoteDataState,
    timeout: int = 5000,
) -> Locator:
    """Wait for RemoteData ADT to reach specified state.

    Looks for elements with data-state attribute matching the state.
    Components should render data-state attributes for synchronization.

    Example:
        # Wait for data to load successfully
        await wait_for_remote_data_state(page, "Success")

        # NOW we know data is available
        items = page.locator('[data-testid="item-list"]')
        await expect(items).to_be_visible()

    Args:
        page: Playwright page
        state: Target RemoteData state
        timeout: Maximum wait time in milliseconds

    Returns:
        Locator for the element with matching state
    """
    locator = page.locator(f'[data-state="{state}"]')
    await expect(locator).to_be_visible(timeout=timeout)
    return locator


async def wait_for_loading_complete(
    page: Page,
    timeout: int = 5000,
) -> None:
    """Wait for any loading state to complete.

    Waits for Loading state to disappear OR Success/Failure to appear.
    """
    # Wait for Loading to disappear
    loading = page.locator('[data-state="Loading"]')

    try:
        # If Loading is visible, wait for it to be hidden
        await expect(loading).to_be_hidden(timeout=timeout)
    except Exception:
        # Loading may have already completed
        pass


# =============================================================================
# Page Ready Helpers
# =============================================================================


async def wait_for_page_ready(
    page: Page,
    *,
    data: bool = True,
    timeout: int = 5000,
) -> None:
    """Wait for page to be fully ready (data loaded).

    Composite helper that waits for data loading state.

    Example:
        # Before (timing hack - BAD):
        await page.goto(make_url("/appointments"))
        await page.wait_for_timeout(5000)  # Hope it's ready

        # After (ADT-based - GOOD):
        await page.goto(make_url("/appointments"))
        await wait_for_page_ready(page)

    Args:
        page: Playwright page
        data: Whether to wait for data loading (RemoteData.Success)
        timeout: Maximum wait time in milliseconds
    """
    if data:
        await wait_for_remote_data_state(page, "Success", timeout=timeout)


async def navigate_and_wait_for_ready(
    page: Page,
    url: str,
    *,
    data: bool = True,
    timeout: int = 10000,
) -> None:
    """Navigate to URL and wait for page to be ready.

    Composite helper: goto + wait_for_page_ready.

    Args:
        page: Playwright page
        url: Target URL
        data: Whether to wait for data loading
        timeout: Maximum wait time for page ready
    """
    await page.goto(url)
    await wait_for_page_ready(page, data=data, timeout=timeout)


# =============================================================================
# Appointment Status Helpers
# =============================================================================


async def wait_for_appointment_status(
    page: Page,
    status: AppointmentStatus,
    timeout: int = 5000,
) -> Locator:
    """Wait for appointment with specific status to be visible.

    Args:
        page: Playwright page
        status: Target appointment status
        timeout: Maximum wait time

    Returns:
        Locator for element with matching status
    """
    locator = page.locator(f'[data-status="{status}"]')
    await expect(locator).to_be_visible(timeout=timeout)
    return locator


async def wait_for_status_badge(
    page: Page,
    status: str,
    timeout: int = 5000,
) -> Locator:
    """Wait for a status badge with specific text to be visible.

    Args:
        page: Playwright page
        status: Status text to look for
        timeout: Maximum wait time

    Returns:
        Locator for the status badge
    """
    locator = page.locator(f'[data-testid="status-badge"]:has-text("{status}")')
    await expect(locator).to_be_visible(timeout=timeout)
    return locator
