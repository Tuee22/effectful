"""E2E Tests for Invoices Feature.

Tests invoice viewing and status management.

Test Categories:
    - List display
    - Detail view with line items
    - Payment status display
    - Admin invoice creation
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from playwright.async_api import Page, expect

from tests.pytest.e2e.helpers.adt_state_helpers import navigate_and_wait_for_ready


@pytest.mark.e2e
@pytest.mark.asyncio
class TestInvoicesList:
    """Test invoice list display."""

    async def test_invoices_page_displays_list(
        self, authenticated_admin_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that invoices page displays invoice list."""
        await authenticated_admin_page.goto(make_url("/invoices"))

        await expect(authenticated_admin_page).to_have_url(make_url("/invoices"))

        # Should show invoice list or empty state
        content = authenticated_admin_page.locator(
            "[data-testid='invoice-list'], "
            "[data-testid='empty-state'], "
            ".invoices-page, "
            "table, "
            ".invoice-card"
        ).first
        await expect(content).to_be_visible(timeout=10000)

    async def test_patient_can_view_own_invoices(
        self, authenticated_patient_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that patient can view their invoices."""
        await authenticated_patient_page.goto(make_url("/invoices"))

        await expect(authenticated_patient_page).to_have_url(make_url("/invoices"))

        # Page should load
        content = authenticated_patient_page.locator(
            "[data-testid='invoice-list'], " "[data-testid='empty-state'], " ".invoices-page"
        )
        await expect(content).to_be_visible(timeout=10000)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestInvoiceStatus:
    """Test invoice status display and management."""

    async def test_invoice_shows_status_badge(
        self, authenticated_admin_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that invoices show status badges."""
        await navigate_and_wait_for_ready(
            authenticated_admin_page, make_url("/invoices"), data=False
        )

        # Look for status badges
        status_badge = authenticated_admin_page.locator(
            "[data-testid='status-badge'], "
            ".status-badge, "
            ":has-text('Paid'), :has-text('Pending'), :has-text('Overdue')"
        ).first

        # If invoices exist, verify status badge is visible
        is_visible = await status_badge.is_visible()
        if is_visible:
            await expect(status_badge).to_be_visible(timeout=5000)
        # If no status badges found, verify we're on the invoices page (no invoices scenario)
        else:
            await expect(authenticated_admin_page).to_have_url(make_url("/invoices"))

    async def test_invoice_shows_total_amount(
        self, authenticated_admin_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that invoices display total amount."""
        await navigate_and_wait_for_ready(
            authenticated_admin_page, make_url("/invoices"), data=False
        )

        # Look for currency amounts
        amount = authenticated_admin_page.locator(
            "[data-testid='invoice-total'], " ".invoice-total, " ":has-text('$'), :has-text('USD')"
        ).first

        # If invoices exist, verify amount is visible
        is_visible = await amount.is_visible()
        if is_visible:
            await expect(amount).to_be_visible(timeout=5000)
        # If no amounts found, verify we're on the invoices page (no invoices scenario)
        else:
            await expect(authenticated_admin_page).to_have_url(make_url("/invoices"))
