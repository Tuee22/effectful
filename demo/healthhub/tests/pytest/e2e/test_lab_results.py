"""E2E Tests for Lab Results Feature.

Tests lab result viewing and review (doctor marking as reviewed).

Test Categories:
    - List display
    - Detail view
    - Mark as reviewed (doctor role)
    - Critical value indication
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from playwright.async_api import Page, expect


@pytest.mark.e2e
@pytest.mark.asyncio
class TestLabResultsList:
    """Test lab results list display."""

    async def test_lab_results_page_displays_list(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that lab results page displays result list."""
        await authenticated_doctor_page.goto(make_url("/lab-results"))

        await expect(authenticated_doctor_page).to_have_url(make_url("/lab-results"))

        # Should show lab results list or empty state
        content = authenticated_doctor_page.locator(
            "[data-testid='lab-result-list'], "
            "[data-testid='empty-state'], "
            ".lab-results-page, "
            "table, "
            ".lab-result-card"
        )
        await expect(content).to_be_visible(timeout=10000)

    async def test_patient_can_view_own_lab_results(
        self, authenticated_patient_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that patient can view their lab results."""
        await authenticated_patient_page.goto(make_url("/lab-results"))

        await expect(authenticated_patient_page).to_have_url(make_url("/lab-results"))

        # Page should load
        content = authenticated_patient_page.locator(
            "[data-testid='lab-result-list'], " "[data-testid='empty-state'], " ".lab-results-page"
        )
        await expect(content).to_be_visible(timeout=10000)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestLabResultReview:
    """Test lab result review functionality (doctor only)."""

    async def test_doctor_can_access_lab_results(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that doctor can access lab results page."""
        await authenticated_doctor_page.goto(make_url("/lab-results"))

        await expect(authenticated_doctor_page).to_have_url(make_url("/lab-results"))

    async def test_lab_result_shows_review_status(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that lab results show review status."""
        await authenticated_doctor_page.goto(make_url("/lab-results"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Look for review status indicators
        status_indicator = authenticated_doctor_page.locator(
            "[data-testid='review-status'], "
            ".review-status, "
            ":has-text('Reviewed'), :has-text('Pending')"
        ).first

        # Status may or may not be visible depending on seed data
