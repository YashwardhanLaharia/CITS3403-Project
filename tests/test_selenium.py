"""
Selenium end-to-end tests for SplitMate.

Uses a live Flask test server + Chrome WebDriver to exercise real
user flows through the browser.

Prerequisites:
    pip install selenium
    ChromeDriver on PATH (or use webdriver-manager)

Run:
    pytest tests/test_selenium.py -v
"""

import threading
import time
import urllib.request
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app import create_app
from extensions import db as _db
from models import User, Group, Membership


BASE_URL = 'http://localhost:5001'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(driver, email, password):
    """Log in via the browser and wait for the home page."""
    driver.get(BASE_URL + '/login')
    driver.find_element(By.NAME, 'email').send_keys(email)
    driver.find_element(By.NAME, 'password').send_keys(password)
    driver.find_element(By.CSS_SELECTOR, '.btn-primary-action').click()
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), 'Welcome back')
    )


def _seed_user(app, email='test@example.com', first='Test', last='User',
               password='Password123!'):
    """Create a user in the DB and return the email for login."""
    with app.app_context():
        user = User(email=email, first_name=first, last_name=last)
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
    return email


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def app():
    """Create the Flask app and start a live server in a background thread."""
    application = create_app('testing')
    with application.app_context():
        _db.create_all()

    thread = threading.Thread(
        target=lambda: application.run(port=5001, use_reloader=False)
    )
    thread.daemon = True
    thread.start()

    # Wait for server to be ready instead of a fixed sleep
    for _ in range(20):
        try:
            urllib.request.urlopen(BASE_URL + '/login')
            break
        except Exception:
            time.sleep(0.25)

    yield application

    with application.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Wipe all table data between tests for isolation."""
    yield
    with app.app_context():
        meta = _db.metadata
        for table in reversed(meta.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture(scope='function')
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    d = webdriver.Chrome(options=options)
    d.implicitly_wait(5)
    yield d
    d.quit()


# ---------------------------------------------------------------------------
# Auth flows
# ---------------------------------------------------------------------------

class TestSignup:
    """Registration form validation and success."""

    def test_signup_with_valid_details(self, app, driver):
        """Fill out all fields, submit, verify redirect to home page."""
        driver.get(BASE_URL + '/signup')
        driver.find_element(By.NAME, 'first_name').send_keys('Test')
        driver.find_element(By.NAME, 'last_name').send_keys('User')
        driver.find_element(By.NAME, 'email').send_keys('testuser@example.com')
        driver.find_element(By.NAME, 'password').send_keys('Password123!')
        driver.find_element(By.NAME, 'confirm_password').send_keys('Password123!')
        driver.find_element(By.CSS_SELECTOR, '.btn-primary-action').click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), 'Welcome back')
        )

    def test_signup_duplicate_email(self, app, driver):
        """Register twice with the same email, verify error message shows."""
        _seed_user(app, email='dupe@example.com')
        driver.get(BASE_URL + '/signup')
        driver.find_element(By.NAME, 'first_name').send_keys('Another')
        driver.find_element(By.NAME, 'last_name').send_keys('User')
        driver.find_element(By.NAME, 'email').send_keys('dupe@example.com')
        driver.find_element(By.NAME, 'password').send_keys('Password123!')
        driver.find_element(By.NAME, 'confirm_password').send_keys('Password123!')
        driver.find_element(By.CSS_SELECTOR, '.btn-primary-action').click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.TAG_NAME, 'body'), 'An account with this email already exists'
            )
        )
        assert '/signup' in driver.current_url

    def test_signup_password_mismatch(self, app, driver):
        """Mismatched confirm password, verify form shows validation error."""
        driver.get(BASE_URL + '/signup')
        driver.find_element(By.NAME, 'first_name').send_keys('Test')
        driver.find_element(By.NAME, 'last_name').send_keys('User')
        driver.find_element(By.NAME, 'email').send_keys('mismatch@example.com')
        driver.find_element(By.NAME, 'password').send_keys('Password123!')
        driver.find_element(By.NAME, 'confirm_password').send_keys('DifferentPass!')
        driver.find_element(By.CSS_SELECTOR, '.btn-primary-action').click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.TAG_NAME, 'body'), 'Passwords do not match'
            )
        )
        assert '/signup' in driver.current_url

    def test_signup_missing_fields(self, app, driver):
        """Submit with required fields blank, verify browser validation."""
        pytest.skip("not implemented")


class TestLogin:
    """Login, logout, and protected page redirects."""

    def test_login_valid_credentials(self, app, driver):
        """Log in with a registered user, verify we land on the home page."""
        _seed_user(app, email='logintest@example.com', first='Login', last='Test')
        _login(driver, 'logintest@example.com', 'Password123!')

    def test_login_wrong_password(self, app, driver):
        """Wrong password shows an error flash, stays on login page."""
        _seed_user(app, email='wrongpw@example.com')
        driver.get(BASE_URL + '/login')
        driver.find_element(By.NAME, 'email').send_keys('wrongpw@example.com')
        driver.find_element(By.NAME, 'password').send_keys('WrongPassword!')
        driver.find_element(By.CSS_SELECTOR, '.btn-primary-action').click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.TAG_NAME, 'body'), 'Invalid email or password'
            )
        )
        assert '/login' in driver.current_url

    def test_protected_page_redirects_to_login(self, app, driver):
        """Hitting /profile without auth redirects to /login."""
        driver.get(BASE_URL + '/profile')
        WebDriverWait(driver, 10).until(EC.url_contains('/login'))
        assert '/login' in driver.current_url

    def test_logout(self, app, driver):
        """Log out via sidebar, verify redirect to login page."""
        _seed_user(app, email='logouttest@example.com', first='Logout', last='Test')
        _login(driver, 'logouttest@example.com', 'Password123!')
        driver.find_element(By.CSS_SELECTOR, '.sidebar-bottom form button[type="submit"]').click()
        WebDriverWait(driver, 10).until(
            EC.url_contains('/login')
        )


# ---------------------------------------------------------------------------
# Group management
# ---------------------------------------------------------------------------

class TestGroups:
    """Creating, joining, and viewing groups."""

    def test_create_group(self, app, driver):
        """Open create group modal, fill name + currency, submit,
        verify group appears on home page."""
        _seed_user(app, email='grouptest@example.com', first='Group', last='Test')
        _login(driver, 'grouptest@example.com', 'Password123!')
        driver.find_element(By.CSS_SELECTOR, '[data-bs-target="#createGroupModal"]').click()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'createGroupModal'))
        )
        driver.find_element(By.NAME, 'group_name').send_keys('Sydney Trip')
        driver.find_element(By.NAME, 'currency').send_keys('AUD')
        driver.find_element(By.CSS_SELECTOR, '#createGroupModal button[type="submit"]').click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), 'Sydney Trip')
        )

    def test_join_group_valid_code(self, app, driver):
        """Enter a valid invite code, submit, verify membership."""
        with app.app_context():
            user = User(email='joiner@example.com', first_name='Join', last_name='Test')
            user.set_password('Password123!')
            _db.session.add(user)
            _db.session.flush()
            owner = User(email='owner@example.com', first_name='Owner', last_name='Test')
            owner.set_password('Password123!')
            _db.session.add(owner)
            _db.session.flush()
            group = Group(
                name='Trip Group',
                currency='AUD',
                invite_code='TESTCODE',
                created_by=owner.id
            )
            _db.session.add(group)
            _db.session.flush()
            _db.session.add(Membership(
                user_id=owner.id, group_id=group.id, role='admin'
            ))
            _db.session.commit()

        _login(driver, 'joiner@example.com', 'Password123!')
        driver.find_element(By.NAME, 'invite_code').send_keys('TESTCODE')
        driver.find_element(By.CSS_SELECTOR, '.btn-join').click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.TAG_NAME, 'body'), 'You have joined'
            )
        )

    def test_join_group_invalid_code(self, app, driver):
        """Enter a bogus invite code, verify error flash."""
        _seed_user(app, email='badcode@example.com', first='Bad', last='Code')
        _login(driver, 'badcode@example.com', 'Password123!')
        driver.find_element(By.NAME, 'invite_code').send_keys('XXXXXXXX')
        driver.find_element(By.CSS_SELECTOR, '.btn-join').click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.TAG_NAME, 'body'), 'Invalid invite code'
            )
        )

    def test_group_dashboard_loads(self, app, driver):
        """Navigate to a group dashboard, verify key sections render:
        member balances, expense distribution, recent activity, settlement."""
        with app.app_context():
            user = User(
                email='dashtest@example.com',
                first_name='Dash',
                last_name='Test'
            )
            user.set_password('Password123!')
            _db.session.add(user)
            _db.session.flush()
            group = Group(
                name='Dashboard Group',
                currency='AUD',
                invite_code=Group.generate_invite_code(),
                created_by=user.id
            )
            _db.session.add(group)
            _db.session.flush()
            _db.session.add(Membership(
                user_id=user.id, group_id=group.id, role='admin'
            ))
            _db.session.commit()
            group_id = group.id

        _login(driver, 'dashtest@example.com', 'Password123!')
        driver.get(BASE_URL + f'/groups/{group_id}')
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), 'Member Balances')
        )
        assert 'Recent Activity' in driver.find_element(By.TAG_NAME, 'body').text
        assert 'Settlement Preview' in driver.find_element(By.TAG_NAME, 'body').text


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

class TestExpenses:
    """Adding expenses through the modal (AJAX submission)."""

    def test_add_equal_split_expense(self, app, driver):
        """Open expense modal, fill details with equal split, submit,
        verify expense appears in recent activity without page reload."""
        pytest.skip("not implemented")

    def test_add_custom_split_expense(self, app, driver):
        """Toggle to custom split, enter per-member amounts, submit,
        verify amounts are correct in the dashboard."""
        pytest.skip("not implemented")

    def test_expense_validation_rejects_empty(self, app, driver):
        """Submit modal with no description/amount, verify error shows
        inside the modal (not a page redirect)."""
        pytest.skip("not implemented")

    def test_expense_updates_balances(self, app, driver):
        """After adding an expense, verify the member balance cards
        update to reflect the new totals."""
        pytest.skip("not implemented")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class TestProfile:
    """Profile viewing and editing."""

    def test_profile_displays_user_info(self, app, driver):
        """Navigate to profile, verify name and email are populated."""
        _seed_user(app, email='profile@example.com', first='Alice', last='Smith')
        _login(driver, 'profile@example.com', 'Password123!')
        driver.get(BASE_URL + '/profile')
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'first-name'))
        )
        assert driver.find_element(By.ID, 'first-name').get_attribute('value') == 'Alice'
        assert driver.find_element(By.ID, 'last-name').get_attribute('value') == 'Smith'
        assert driver.find_element(By.ID, 'email').get_attribute('value') == 'profile@example.com'

    def test_profile_update_name(self, app, driver):
        """Change first name, enter current password, submit, verify
        the updated name shows on reload."""
        pytest.skip("not implemented")


# ---------------------------------------------------------------------------
# Navigation and responsive UI
# ---------------------------------------------------------------------------

class TestNavigation:
    """Sidebar, hamburger menu, and page transitions."""

    def test_sidebar_links_navigate(self, app, driver):
        """Click Home and Dashboard in the sidebar, verify correct
        pages load."""
        pytest.skip("not implemented")

    def test_hamburger_menu_on_mobile(self, app, driver):
        """Resize viewport to mobile width, verify hamburger button
        appears and toggles the sidebar."""
        pytest.skip("not implemented")
