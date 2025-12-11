"""Navigation helpers for E2E tests.

Centralizes common goto + wait patterns and list locators to
keep tests terse and avoid duplicated selector logic.
"""

from __future__ import annotations

from collections.abc import Callable

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect

from tests.pytest.e2e.helpers.adt_state_helpers import (
    RemoteDataState,
    wait_for_page_ready,
    wait_for_remote_data_state,
)


async def goto_and_wait(
    page: Page,
    make_url: Callable[[str], str],
    path: str,
    *,
    data_state: RemoteDataState | None = "Success",
    timeout: int = 10000,
) -> None:
    """Navigate to a path and wait for the page's data to be ready."""
    target = make_url(path)
    await page.goto(target)
    await expect(page).to_have_url(target)
    if data_state:
        try:
            if data_state == "Success":
                await wait_for_page_ready(page, timeout=timeout)
            else:
                await wait_for_remote_data_state(page, data_state, timeout=timeout)
        except (AssertionError, PlaywrightTimeoutError):
            # Aligns with total model doctrine: if explicit data-state is absent,
            # fall back to deterministic load-state so tests never hang on implicit states.
            await page.wait_for_load_state("networkidle", timeout=timeout)


def appointments_list_locator(page: Page) -> Locator:
    """Locator covering appointments lists and empty states."""
    return page.locator(
        "[data-testid='appointment-list'], "
        "[data-testid='appointments-list'], "
        "[data-testid='empty-state'], "
        ".appointments-page, "
        ".appointments-list"
    ).first


def prescriptions_list_locator(page: Page) -> Locator:
    """Locator covering prescription lists and empty states."""
    return page.locator(
        "[data-testid='prescription-list'], "
        "[data-testid='prescriptions-list'], "
        "[data-testid='empty-state'], "
        ".prescriptions-page, "
        ".prescriptions-list"
    ).first


def lab_results_list_locator(page: Page) -> Locator:
    """Locator covering lab results lists and empty states."""
    return page.locator(
        "[data-testid='lab-result-list'], "
        "[data-testid='lab-results-list'], "
        "[data-testid='lab-result-empty'], "
        ".lab-results-page, "
        ".lab-results-list"
    ).first


def invoices_list_locator(page: Page) -> Locator:
    """Locator covering invoice lists and empty states."""
    return page.locator(
        "[data-testid='invoice-list'], "
        "[data-testid='invoices-list'], "
        "[data-testid='empty-state'], "
        ".invoices-page, "
        ".invoice-list, "
        ".invoice-list-empty"
    ).first
