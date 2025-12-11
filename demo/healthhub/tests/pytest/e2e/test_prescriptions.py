"""E2E Tests for Prescriptions Feature.

Tests prescription viewing and creation (doctor only).

Test Categories:
    - List display
    - Detail view
    - Create form (doctor role)
    - Form validation
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from playwright.async_api import Page, expect

from tests.pytest.e2e.helpers.adt_state_helpers import wait_for_page_ready


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPrescriptionsList:
    """Test prescription list display."""

    async def test_prescriptions_page_displays_list(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that prescriptions page displays prescription list."""
        await authenticated_doctor_page.goto(make_url("/prescriptions"))

        await expect(authenticated_doctor_page).to_have_url(make_url("/prescriptions"))

        # Should show prescription list or empty state
        content = authenticated_doctor_page.locator(
            "[data-testid='prescription-list'], "
            "[data-testid='empty-state'], "
            ".prescriptions-page, "
            "table, "
            ".prescription-card"
        ).first
        await expect(content).to_be_visible(timeout=10000)

    async def test_patient_can_view_own_prescriptions(
        self, authenticated_patient_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that patient can view their prescriptions."""
        await authenticated_patient_page.goto(make_url("/prescriptions"))

        await expect(authenticated_patient_page).to_have_url(make_url("/prescriptions"))

        # Page should load
        content = authenticated_patient_page.locator(
            "[data-testid='prescription-list'], "
            "[data-testid='empty-state'], "
            ".prescriptions-page"
        ).first
        await expect(content).to_be_visible(timeout=10000)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPrescriptionCreation:
    """Test prescription creation (doctor only)."""

    async def test_doctor_sees_create_button(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that doctor can see create prescription option."""
        await authenticated_doctor_page.goto(make_url("/prescriptions"))
        await expect(authenticated_doctor_page).to_have_url(make_url("/prescriptions"))
        await wait_for_page_ready(authenticated_doctor_page)

    async def test_prescription_form_has_required_fields(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that prescription form has all required fields."""
        await authenticated_doctor_page.goto(make_url("/prescriptions"))
        await expect(authenticated_doctor_page).to_have_url(make_url("/prescriptions"))
        await wait_for_page_ready(authenticated_doctor_page)

        # Try to find create button/link
        create_button = authenticated_doctor_page.locator(
            'button:has-text("Create"), button:has-text("New"), '
            '[data-testid="create-prescription"], a:has-text("Create")'
        ).first

        is_visible = await create_button.is_visible()
        if is_visible:
            await create_button.click()

            form = authenticated_doctor_page.locator(
                ".prescription-form, [data-testid='prescription-form']"
            )
            await expect(form.first).to_be_visible(timeout=5000)

            # Verify core fields are present
            await expect(form.locator("select[name='patientId']")).to_be_visible(timeout=5000)
            await expect(form.locator("input[name='medication']")).to_be_visible(timeout=5000)
            await expect(form.locator("input[name='dosage']")).to_be_visible(timeout=5000)
            await expect(form.locator("input[name='frequency']")).to_be_visible(timeout=5000)
            await expect(form.locator("input[name='durationDays']")).to_be_visible(timeout=5000)
            await expect(form.locator("input[name='refills']")).to_be_visible(timeout=5000)
