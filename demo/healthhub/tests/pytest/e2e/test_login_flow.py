"""E2E Tests for User Login Flow.

Tests the authentication state machine with real browser interactions via Playwright.
NO httpx calls - these are true end-to-end UI tests.

State Machine:
    Hydrating → Unauthenticated → Authenticating → Authenticated
                                                 → AuthenticationFailed

Test Categories:
    - Form rendering and validation
    - Successful login flows for each role
    - Failed login scenarios
    - Session persistence and logout
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from playwright.async_api import Page, expect

from tests.pytest.e2e.helpers.auth_helpers import (
    TEST_USERS,
    get_auth_state,
    is_authenticated,
    wait_for_auth_hydration,
)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestLoginPageRendering:
    """Test login page form rendering and validation."""

    async def test_login_page_displays_form_elements(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that login page renders all form elements correctly."""
        await page.goto(make_url("/login"))

        # Verify page title/header
        await expect(page.locator("h1, h2").first).to_be_visible()

        # Verify form fields
        email_input = page.locator('input[name="email"]')
        await expect(email_input).to_be_visible()
        await expect(email_input).to_have_attribute("type", "email")

        password_input = page.locator('input[name="password"]')
        await expect(password_input).to_be_visible()
        await expect(password_input).to_have_attribute("type", "password")

        # Verify submit button
        submit_button = page.locator('button[type="submit"]')
        await expect(submit_button).to_be_visible()
        await expect(submit_button).to_be_enabled()

    async def test_login_form_shows_validation_for_empty_email(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that form validates empty email field."""
        await page.goto(make_url("/login"))

        # Fill password but leave email empty
        await page.locator('input[name="password"]').fill("somepassword")

        # Try to submit
        await page.locator('button[type="submit"]').click()

        # Form should not navigate away (browser validation)
        await expect(page).to_have_url(make_url("/login"))

    async def test_login_form_shows_validation_for_empty_password(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that form validates empty password field."""
        await page.goto(make_url("/login"))

        # Fill email but leave password empty
        await page.locator('input[name="email"]').fill("test@example.com")

        # Try to submit
        await page.locator('button[type="submit"]').click()

        # Form should not navigate away (browser validation)
        await expect(page).to_have_url(make_url("/login"))


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSuccessfulLogin:
    """Test successful login flows for each role."""

    async def test_patient_login_redirects_to_dashboard(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test successful patient login redirects to dashboard."""
        await page.goto(make_url("/login"))

        patient = TEST_USERS["patient"]
        await page.locator('input[name="email"]').fill(patient["email"])
        await page.locator('input[name="password"]').fill(patient["password"])
        await page.locator('button[type="submit"]').click()

        # Wait for redirect to dashboard
        await page.wait_for_url(make_url("/dashboard"), timeout=10000)

        # Verify auth state
        await wait_for_auth_hydration(page)
        assert await is_authenticated(page)

    async def test_doctor_login_redirects_to_dashboard(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test successful doctor login redirects to dashboard."""
        await page.goto(make_url("/login"))

        doctor = TEST_USERS["doctor"]
        await page.locator('input[name="email"]').fill(doctor["email"])
        await page.locator('input[name="password"]').fill(doctor["password"])
        await page.locator('button[type="submit"]').click()

        # Wait for redirect to dashboard
        await page.wait_for_url(make_url("/dashboard"), timeout=10000)

        # Verify auth state
        await wait_for_auth_hydration(page)
        assert await is_authenticated(page)

    async def test_admin_login_redirects_to_dashboard(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test successful admin login redirects to dashboard."""
        await page.goto(make_url("/login"))

        admin = TEST_USERS["admin"]
        await page.locator('input[name="email"]').fill(admin["email"])
        await page.locator('input[name="password"]').fill(admin["password"])
        await page.locator('button[type="submit"]').click()

        # Wait for redirect to dashboard
        await page.wait_for_url(make_url("/dashboard"), timeout=10000)

        # Verify auth state
        await wait_for_auth_hydration(page)
        assert await is_authenticated(page)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestFailedLogin:
    """Test failed login scenarios."""

    async def test_invalid_credentials_shows_error(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that invalid credentials display an error message."""
        await page.goto(make_url("/login"))

        # Use invalid credentials
        await page.locator('input[name="email"]').fill("wrong@example.com")
        await page.locator('input[name="password"]').fill("wrongpassword")
        await page.locator('button[type="submit"]').click()

        # Should stay on login page - wait for error message to appear
        error_locator = page.locator(
            '[data-testid="error-message"], [role="alert"], .error, .alert-error, .login-error'
        )
        await expect(error_locator).to_be_visible(timeout=5000)
        await expect(page).to_have_url(make_url("/login"))

        # Check for error message (various possible selectors)
        error_visible = await page.locator(
            '[data-testid="error-message"], [role="alert"], .error, .alert-error, .login-error'
        ).is_visible()

        # Auth state should be AuthenticationFailed
        state = await get_auth_state(page)
        assert state.get("type") in ["AuthenticationFailed", "Unauthenticated"]

    async def test_invalid_email_format_shows_validation(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that invalid email format triggers validation."""
        await page.goto(make_url("/login"))

        # Use invalid email format
        await page.locator('input[name="email"]').fill("notanemail")
        await page.locator('input[name="password"]').fill("password123")
        await page.locator('button[type="submit"]').click()

        # Browser should prevent submission with invalid email
        await expect(page).to_have_url(make_url("/login"))


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSessionManagement:
    """Test session persistence and logout."""

    async def test_session_persists_across_page_refresh(
        self, authenticated_patient_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that session persists after page refresh (SessionRestorable state)."""
        # Verify we're authenticated
        assert await is_authenticated(authenticated_patient_page)

        # Refresh the page
        await authenticated_patient_page.reload()

        # Wait for auth to hydrate again
        await wait_for_auth_hydration(authenticated_patient_page)

        # Should still be authenticated
        assert await is_authenticated(authenticated_patient_page)

        # Should still be on dashboard (not redirected to login)
        await expect(authenticated_patient_page).to_have_url(make_url("/dashboard"))

    async def test_logout_clears_session_and_redirects(
        self, authenticated_patient_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that logout clears session and redirects to login."""
        # Verify we're authenticated
        assert await is_authenticated(authenticated_patient_page)

        # Find and click logout button
        logout_button = authenticated_patient_page.locator(
            'button:has-text("Logout"), button:has-text("Log out"), '
            'button:has-text("Sign Out"), button:has-text("Sign out"), '
            '[data-testid="logout-button"], a:has-text("Logout")'
        )
        await logout_button.click()

        # Should redirect to login
        await authenticated_patient_page.wait_for_url(make_url("/login"), timeout=5000)

        # Auth state should be cleared
        state = await get_auth_state(authenticated_patient_page)
        assert state.get("type") in ["Unauthenticated", None, {}]

    async def test_protected_route_redirects_unauthenticated_user(
        self, page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that accessing protected route redirects to login."""
        # Try to access dashboard without authentication
        await page.goto(make_url("/dashboard"))

        # Should be redirected to login
        await page.wait_for_url(make_url("/login"), timeout=5000)
        await expect(page).to_have_url(make_url("/login"))
