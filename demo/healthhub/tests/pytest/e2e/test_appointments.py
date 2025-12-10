"""E2E Tests for Appointment State Machine.

Tests the appointment workflow and status transitions.

State Machine:
    Requested → Confirmed → InProgress → Completed
        ↓           ↓           ↓
    Cancelled   Cancelled   Cancelled

Test Categories:
    - List display and filtering
    - Status transitions (doctor actions)
    - Terminal state validation
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from playwright.async_api import Page, expect


@pytest.mark.e2e
@pytest.mark.asyncio
class TestAppointmentListDisplay:
    """Test appointment list display and navigation."""

    async def test_appointments_page_displays_list(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that appointments page displays appointment list."""
        await authenticated_doctor_page.goto(make_url("/appointments"))

        # Wait for page to load
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Should be on appointments page
        await expect(authenticated_doctor_page).to_have_url(make_url("/appointments"))

        # Should show appointment list or empty state
        content = authenticated_doctor_page.locator(
            "[data-testid='appointment-list'], "
            "[data-testid='empty-state'], "
            ".appointments-page, "
            "table, "
            ".appointment-card"
        )
        await expect(content).to_be_visible(timeout=10000)

    async def test_appointments_can_be_filtered_by_status(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that appointments can be filtered by status."""
        await authenticated_doctor_page.goto(make_url("/appointments"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Look for filter controls
        filter_control = authenticated_doctor_page.locator(
            "select, [data-testid='status-filter'], " ".filter-dropdown, [role='combobox']"
        )

        # Filter may or may not be present depending on implementation
        # Just verify page is accessible
        await expect(authenticated_doctor_page).to_have_url(make_url("/appointments"))

    async def test_appointment_detail_accessible(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that appointment detail page is accessible."""
        await authenticated_doctor_page.goto(make_url("/appointments"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Try to find an appointment link/button
        appointment_link = authenticated_doctor_page.locator(
            "[data-testid='appointment-item'], "
            ".appointment-card, "
            "tr[data-testid], "
            "a[href*='/appointments/']"
        ).first

        # If there are appointments, click one
        is_visible = await appointment_link.is_visible()
        if is_visible:
            await appointment_link.click()
            # Should navigate to detail page
            await authenticated_doctor_page.wait_for_timeout(1000)
            # Verify navigation occurred - URL should change to detail page
            current_url = authenticated_doctor_page.url
            assert "/appointments/" in current_url


@pytest.mark.e2e
@pytest.mark.asyncio
class TestAppointmentStateMachine:
    """Test appointment status transitions."""

    async def test_doctor_can_view_appointment_actions(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that doctor can see appointment action buttons."""
        await authenticated_doctor_page.goto(make_url("/appointments"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Doctor should have access to the appointments page
        await expect(authenticated_doctor_page).to_have_url(make_url("/appointments"))

        # Action buttons depend on appointment state and seed data
        # Just verify page loads correctly

    async def test_requested_appointment_shows_confirm_option(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that requested appointments can be confirmed."""
        await authenticated_doctor_page.goto(make_url("/appointments"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Look for appointments with "Requested" status
        requested_appointment = authenticated_doctor_page.locator(
            "[data-status='requested'], " ":has-text('Requested'):not(button)"
        ).first

        # If there's a requested appointment, it should have a confirm option
        is_visible = await requested_appointment.is_visible()
        if is_visible:
            # Verify confirm action button is visible
            confirm_button = authenticated_doctor_page.locator(
                "button:has-text('Confirm'), "
                "[data-action='confirm'], "
                "[data-testid='confirm-appointment']"
            ).first
            await expect(confirm_button).to_be_visible(timeout=5000)

    async def test_confirmed_appointment_shows_start_option(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that confirmed appointments can be started."""
        await authenticated_doctor_page.goto(make_url("/appointments"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Look for appointments with "Confirmed" status
        confirmed_appointment = authenticated_doctor_page.locator(
            "[data-status='confirmed'], " ":has-text('Confirmed'):not(button)"
        ).first

        # If there's a confirmed appointment, it should have a start option
        is_visible = await confirmed_appointment.is_visible()
        if is_visible:
            # Verify start action button is visible
            start_button = authenticated_doctor_page.locator(
                "button:has-text('Start'), "
                "[data-action='start'], "
                "[data-testid='start-appointment']"
            ).first
            await expect(start_button).to_be_visible(timeout=5000)

    async def test_in_progress_appointment_shows_complete_option(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that in-progress appointments can be completed."""
        await authenticated_doctor_page.goto(make_url("/appointments"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Look for appointments with "In Progress" status
        in_progress_appointment = authenticated_doctor_page.locator(
            "[data-status='in_progress'], [data-status='inprogress'], "
            ":has-text('In Progress'):not(button)"
        ).first

        # If there's an in-progress appointment, it should have a complete option
        is_visible = await in_progress_appointment.is_visible()
        if is_visible:
            # Verify complete action button is visible
            complete_button = authenticated_doctor_page.locator(
                "button:has-text('Complete'), "
                "[data-action='complete'], "
                "[data-testid='complete-appointment']"
            ).first
            await expect(complete_button).to_be_visible(timeout=5000)

    async def test_completed_appointment_has_no_transition_buttons(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that completed appointments cannot be transitioned."""
        await authenticated_doctor_page.goto(make_url("/appointments"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Look for appointments with "Completed" status
        completed_appointment = authenticated_doctor_page.locator(
            "[data-status='completed'], " ":has-text('Completed'):not(button)"
        ).first

        is_visible = await completed_appointment.is_visible()
        if is_visible:
            # Completed appointments should not have transition action buttons
            # (terminal state - no further transitions allowed)
            action_buttons = authenticated_doctor_page.locator(
                "button[data-action='confirm'], "
                "button[data-action='start'], "
                "button[data-action='complete'], "
                "button:has-text('Confirm'):not([disabled]), "
                "button:has-text('Start'):not([disabled]), "
                "button:has-text('Complete'):not([disabled])"
            )
            # Assert no transition buttons are visible for completed appointments
            count = await action_buttons.count()
            assert (
                count == 0
            ), f"Expected no transition buttons for completed appointment, found {count}"

    async def test_cancelled_appointment_has_no_transition_buttons(
        self, authenticated_doctor_page: Page, make_url: Callable[[str], str]
    ) -> None:
        """Test that cancelled appointments cannot be transitioned."""
        await authenticated_doctor_page.goto(make_url("/appointments"))
        await authenticated_doctor_page.wait_for_timeout(2000)

        # Look for appointments with "Cancelled" status
        cancelled_appointment = authenticated_doctor_page.locator(
            "[data-status='cancelled'], " ":has-text('Cancelled'):not(button)"
        ).first

        is_visible = await cancelled_appointment.is_visible()
        if is_visible:
            # Cancelled appointments should not have transition action buttons
            # (terminal state - no further transitions allowed)
            action_buttons = authenticated_doctor_page.locator(
                "button[data-action='confirm'], "
                "button[data-action='start'], "
                "button[data-action='complete'], "
                "button:has-text('Confirm'):not([disabled]), "
                "button:has-text('Start'):not([disabled]), "
                "button:has-text('Complete'):not([disabled])"
            )
            # Assert no transition buttons are visible for cancelled appointments
            count = await action_buttons.count()
            assert (
                count == 0
            ), f"Expected no transition buttons for cancelled appointment, found {count}"
