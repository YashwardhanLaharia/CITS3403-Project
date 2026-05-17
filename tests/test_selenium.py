"""
Selenium end-to-end tests for SplitMate.

Uses a live Flask test server + Chrome WebDriver to exercise real
user flows through the browser. Each test gets a fresh database.

Prerequisites:
    pip install selenium
    ChromeDriver on PATH (or use webdriver-manager)

Run:
    pytest tests/test_selenium.py -v
"""

import pytest


# ---------------------------------------------------------------------------
# Fixtures (TODO)
# ---------------------------------------------------------------------------
# - live_app: create_app('testing'), init db, run on a free port via
#   threading.Thread, yield base_url, teardown
# - driver: headless Chrome via webdriver.Chrome, quit after test
# - registered_user: sign up a user through the UI, return credentials


# ---------------------------------------------------------------------------
# Auth flows
# ---------------------------------------------------------------------------

class TestSignup:
    """Registration form validation and success."""

    def test_signup_with_valid_details(self):
        """Fill out all fields, submit, verify redirect to home page."""
        pytest.skip("not implemented")

    def test_signup_duplicate_email(self):
        """Register twice with the same email, verify error message shows."""
        pytest.skip("not implemented")

    def test_signup_password_mismatch(self):
        """Mismatched confirm password, verify form shows validation error."""
        pytest.skip("not implemented")

    def test_signup_missing_fields(self):
        """Submit with required fields blank, verify browser validation."""
        pytest.skip("not implemented")


class TestLogin:
    """Login, logout, and protected page redirects."""

    def test_login_valid_credentials(self):
        """Log in with a registered user, verify we land on the home page."""
        pytest.skip("not implemented")

    def test_login_wrong_password(self):
        """Wrong password shows an error flash, stays on login page."""
        pytest.skip("not implemented")

    def test_protected_page_redirects_to_login(self):
        """Hitting /profile without auth redirects to /login."""
        pytest.skip("not implemented")

    def test_logout(self):
        """Log out via sidebar, verify redirect to login page."""
        pytest.skip("not implemented")


# ---------------------------------------------------------------------------
# Group management
# ---------------------------------------------------------------------------

class TestGroups:
    """Creating, joining, and viewing groups."""

    def test_create_group(self):
        """Open create group modal, fill name + currency, submit,
        verify group appears on home page."""
        pytest.skip("not implemented")

    def test_join_group_valid_code(self):
        """Enter a valid invite code, submit, verify membership."""
        pytest.skip("not implemented")

    def test_join_group_invalid_code(self):
        """Enter a bogus invite code, verify error flash."""
        pytest.skip("not implemented")

    def test_group_dashboard_loads(self):
        """Navigate to a group dashboard, verify key sections render:
        member balances, expense distribution, recent activity, settlement."""
        pytest.skip("not implemented")


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

class TestExpenses:
    """Adding expenses through the modal (AJAX submission)."""

    def test_add_equal_split_expense(self):
        """Open expense modal, fill details with equal split, submit,
        verify expense appears in recent activity without page reload."""
        pytest.skip("not implemented")

    def test_add_custom_split_expense(self):
        """Toggle to custom split, enter per-member amounts, submit,
        verify amounts are correct in the dashboard."""
        pytest.skip("not implemented")

    def test_expense_validation_rejects_empty(self):
        """Submit modal with no description/amount, verify error shows
        inside the modal (not a page redirect)."""
        pytest.skip("not implemented")

    def test_expense_updates_balances(self):
        """After adding an expense, verify the member balance cards
        update to reflect the new totals."""
        pytest.skip("not implemented")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class TestProfile:
    """Profile viewing and editing."""

    def test_profile_displays_user_info(self):
        """Navigate to profile, verify name and email are populated."""
        pytest.skip("not implemented")

    def test_profile_update_name(self):
        """Change first name, enter current password, submit, verify
        the updated name shows on reload."""
        pytest.skip("not implemented")


# ---------------------------------------------------------------------------
# Navigation and responsive UI
# ---------------------------------------------------------------------------

class TestNavigation:
    """Sidebar, hamburger menu, and page transitions."""

    def test_sidebar_links_navigate(self):
        """Click Home and Dashboard in the sidebar, verify correct
        pages load."""
        pytest.skip("not implemented")

    def test_hamburger_menu_on_mobile(self):
        """Resize viewport to mobile width, verify hamburger button
        appears and toggles the sidebar."""
        pytest.skip("not implemented")
