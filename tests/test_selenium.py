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

import threading
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app import create_app
from extensions import db as _db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def live_app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        thread = threading.Thread(
            target=lambda: app.run(port=5001, use_reloader=False)
        )
        thread.daemon = True
        thread.start()
        time.sleep(1)
        yield 'http://localhost:5001'
        _db.drop_all()

@pytest.fixture(scope='function')
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    d = webdriver.Chrome(options=options)
    d.implicitly_wait(5)
    yield d
    d.quit()


# ---------------------------------------------------------------------------
# Auth flows
# ---------------------------------------------------------------------------

class TestSignup:
    """Registration form validation and success."""

    def test_signup_with_valid_details(self, live_app, driver):
        """Fill out all fields, submit, verify redirect to home page."""
        driver.get(live_app + '/signup')
        driver.find_element(By.NAME, 'first_name').send_keys('Test')
        driver.find_element(By.NAME, 'last_name').send_keys('User')
        driver.find_element(By.NAME, 'email').send_keys('testuser@example.com')
        driver.find_element(By.NAME, 'password').send_keys('Password123!')
        driver.find_element(By.NAME, 'confirm_password').send_keys('Password123!')
        driver.find_element(By.CSS_SELECTOR, 'form button[type="submit"]').click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), 'Welcome back')
        )

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
