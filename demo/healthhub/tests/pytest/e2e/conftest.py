"""E2E Test Fixtures for HealthHub.

Follows ShipNorth patterns for Playwright testing:
- Function-scoped browser fixtures (prevents resource exhaustion)
- ADT state synchronization (no timing hacks)
- Storage clearing after each test (prevents auth token leakage)
- Authenticated fixtures for each role (patient, doctor, admin)
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
import redis.asyncio as redis
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from tests.pytest.e2e.helpers.auth_helpers import wait_for_auth_hydration

if TYPE_CHECKING:
    from pytest import FixtureRequest


# =============================================================================
# Configuration
# =============================================================================


@pytest.fixture(scope="session")
def base_url() -> str:
    """Get the frontend base URL for E2E tests.

    Single-source: FastAPI serves the built frontend on port 8851.
    """
    return "http://localhost:8851"


@pytest.fixture(scope="session")
def backend_url() -> str:
    """Get the backend base URL for E2E tests."""
    return "http://localhost:8851"


# =============================================================================
# URL Helper
# =============================================================================


@pytest.fixture
def make_url(base_url: str) -> Callable[[str], str]:
    """Create a URL builder function."""

    def _make_url(path: str) -> str:
        """Build full URL from path."""
        return f"{base_url}{path}"

    return _make_url


# =============================================================================
# Browser Fixtures (ShipNorth Pattern - Function Scoped)
# =============================================================================


# Docker-specific chromium args for stability
CHROMIUM_DOCKER_ARGS: list[str] = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-dbus",  # Critical for Docker!
    "--disable-notifications",
]

# NOTE: Redis cleanup (including rate limits) is handled by clean_healthhub_state
# fixture in parent conftest.py. No need for separate autouse fixture here.


@pytest_asyncio.fixture(scope="function", params=["chromium", "firefox", "webkit"])
async def browser(request: FixtureRequest) -> AsyncGenerator[Browser, None]:
    """Launch browser for E2E tests.

    Uses function scope to ensure each test gets a fresh browser instance.
    This prevents resource exhaustion and connection issues in long test runs.

    ShipNorth pattern: Function-scoped, parametrized for all 3 browsers.
    """
    browser_name = str(request.param)

    async with async_playwright() as p:
        # Launch with browser-specific options
        if browser_name == "chromium":
            browser_instance = await p.chromium.launch(
                headless=True,
                timeout=30000,
                args=CHROMIUM_DOCKER_ARGS,
            )
        elif browser_name == "firefox":
            browser_instance = await p.firefox.launch(
                headless=True,
                timeout=30000,
            )
        else:  # webkit
            browser_instance = await p.webkit.launch(
                headless=True,
                timeout=30000,
            )

        yield browser_instance
        await browser_instance.close()


@pytest_asyncio.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create a new browser context for each test.

    CRITICAL (ShipNorth pattern): Clears localStorage and sessionStorage after
    each test to ensure test isolation. Without this, auth tokens leak between tests.
    """
    context = await browser.new_context(viewport={"width": 1280, "height": 720})
    yield context

    # CRITICAL: Clear all storage before closing context
    for page in context.pages:
        try:
            await page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        except Exception:
            pass  # Page may already be closed

    await context.close()


@pytest_asyncio.fixture
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a new page for each test."""
    page = await context.new_page()

    # Capture browser console messages for debugging
    page.on("console", lambda msg: print(f"[Browser {msg.type.upper()}]: {msg.text}"))

    # Set timeouts for navigation and assertions
    # Firefox needs longer timeouts for form submissions
    page.set_default_timeout(15000)  # 15 second timeout for actions
    page.set_default_navigation_timeout(15000)  # 15 second timeout for navigation

    yield page
    await page.close()


# =============================================================================
# Authenticated Page Fixtures (ShipNorth Pattern)
# =============================================================================


@pytest_asyncio.fixture
async def authenticated_patient_page(browser: Browser, base_url: str) -> AsyncGenerator[Page, None]:
    """Create an authenticated page logged in as a patient.

    Uses alice.patient@example.com from seed data.
    Creates its own browser context for isolation when multiple auth fixtures are used.
    """
    # Create isolated context for this fixture
    context = await browser.new_context(viewport={"width": 1280, "height": 720})
    page = await context.new_page()
    page.on("console", lambda msg: print(f"[Browser {msg.type.upper()}]: {msg.text}"))
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(15000)

    # Navigate to login
    await page.goto(f"{base_url}/login")

    # Wait for React to render the login form
    await page.wait_for_selector('input[name="email"]', timeout=15000)

    # Fill in patient credentials (from seed_data.sql)
    await page.locator('input[name="email"]').fill("alice.patient@example.com")
    await page.locator('input[name="password"]').fill("password123")

    # Submit form with async navigation handling for Firefox stability
    async with page.expect_navigation(timeout=30000):
        await page.locator('button[type="submit"]').click()

    # Wait for redirect to dashboard with extended timeout
    await page.wait_for_url(f"{base_url}/dashboard", timeout=30000)

    # CRITICAL: Wait for auth store to hydrate from localStorage
    await wait_for_auth_hydration(page, timeout_ms=10000)

    yield page

    # Close page and context
    await page.close()
    await context.close()


@pytest_asyncio.fixture
async def authenticated_doctor_page(browser: Browser, base_url: str) -> AsyncGenerator[Page, None]:
    """Create an authenticated page logged in as a doctor.

    Uses dr.smith@healthhub.com from seed data.
    Creates its own browser context for isolation when multiple auth fixtures are used.
    """
    # Create isolated context for this fixture
    context = await browser.new_context(viewport={"width": 1280, "height": 720})
    page = await context.new_page()
    page.on("console", lambda msg: print(f"[Browser {msg.type.upper()}]: {msg.text}"))
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(15000)

    # Navigate to login
    await page.goto(f"{base_url}/login")

    # Wait for React to render the login form
    await page.wait_for_selector('input[name="email"]', timeout=15000)

    # Fill in doctor credentials (from seed_data.sql)
    await page.locator('input[name="email"]').fill("dr.smith@healthhub.com")
    await page.locator('input[name="password"]').fill("password123")

    # Submit form with async navigation handling for Firefox stability
    async with page.expect_navigation(timeout=30000):
        await page.locator('button[type="submit"]').click()

    # Wait for redirect to dashboard with extended timeout
    await page.wait_for_url(f"{base_url}/dashboard", timeout=30000)

    # CRITICAL: Wait for auth store to hydrate from localStorage
    await wait_for_auth_hydration(page, timeout_ms=10000)

    yield page

    # Close page and context
    await page.close()
    await context.close()


@pytest_asyncio.fixture
async def authenticated_admin_page(browser: Browser, base_url: str) -> AsyncGenerator[Page, None]:
    """Create an authenticated page logged in as an admin.

    Uses admin@healthhub.com from seed data.
    Creates its own browser context for isolation when multiple auth fixtures are used.
    """
    # Create isolated context for this fixture
    context = await browser.new_context(viewport={"width": 1280, "height": 720})
    page = await context.new_page()
    page.on("console", lambda msg: print(f"[Browser {msg.type.upper()}]: {msg.text}"))
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(15000)

    # Navigate to login
    await page.goto(f"{base_url}/login")

    # Wait for React to render the login form
    await page.wait_for_selector('input[name="email"]', timeout=15000)

    # Fill in admin credentials (from seed_data.sql)
    await page.locator('input[name="email"]').fill("admin@healthhub.com")
    await page.locator('input[name="password"]').fill("password123")

    # Submit form with async navigation handling for Firefox stability
    async with page.expect_navigation(timeout=30000):
        await page.locator('button[type="submit"]').click()

    # Wait for redirect to dashboard with extended timeout
    await page.wait_for_url(f"{base_url}/dashboard", timeout=30000)

    # CRITICAL: Wait for auth store to hydrate from localStorage
    await wait_for_auth_hydration(page, timeout_ms=10000)

    yield page

    # Close page and context
    await page.close()
    await context.close()


# =============================================================================
# Test Data Isolation (ShipNorth Pattern)
# =============================================================================

# NOTE: Test data isolation is provided by the clean_healthhub_state fixture
# in parent conftest.py. This fixture ensures every test starts with the same
# deterministic state by:
#   1. Truncating all PostgreSQL tables
#   2. Loading seed_data.sql (2 admins, 4 doctors, 5 patients + sample data)
#   3. Clearing all Redis keys (cache, rate limits, notifications)
#
# The auto_clean_healthhub_state fixture below automatically applies this
# to all e2e tests via autouse=True.


@pytest_asyncio.fixture(autouse=True)
async def auto_clean_healthhub_state(
    clean_healthhub_state: None,
) -> AsyncGenerator[None, None]:
    """Automatically apply clean_healthhub_state to all e2e tests.

    This autouse fixture ensures every e2e test starts with idempotent base state
    without requiring manual fixture injection in each test function signature.

    The fixture simply depends on clean_healthhub_state from parent conftest.py,
    which handles all the actual cleanup and seeding logic.
    """
    yield
