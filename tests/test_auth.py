import pytest
from datetime import datetime, timezone

from models import User
from extensions import db


def test_signup_validation_errors(client):
    response = client.post(
        '/signup',
        data={
            'first_name': '',
            'last_name': '',
            'email': 'invalid',
            'password': 'short',
            'confirm_password': 'nomatch',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert User.query.count() == 0


def test_signup_creates_user(client):
    payload = {
        'first_name': 'Alice',
        'last_name': 'Doe',
        'email': 'alice@example.com',
        'password': 'Secret123!',
        'confirm_password': 'Secret123!',
    }

    response = client.post('/signup', data=payload, follow_redirects=True)
    assert b'Registration successful!' in response.data

    user = User.query.filter_by(email='alice@example.com').first()
    assert user is not None
    assert user.first_name == 'Alice'


def test_login_and_logout_flow(client, user_factory):
    user, password = user_factory()

    response = client.post(
        '/login',
        data={'email': user.email, 'password': password},
        follow_redirects=True,
    )
    assert b'Welcome back' in response.data

    response = client.post('/logout', follow_redirects=True)
    assert b'You have been logged out.' in response.data


def test_index_requires_login(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


@pytest.mark.parametrize("credential_type,credential_value,expected_message", [
    ("nonexistent_email", "nonexistent@example.com", "Invalid email or password."),
    ("wrong_password", "WrongPassword123!", "Invalid email or password."),
])
def test_login_with_invalid_credentials(client, user_factory, credential_type, credential_value, expected_message):
    if credential_type == "nonexistent_email":
        email = credential_value
        password = "anypass"
    else:
        user, _ = user_factory()
        email = user.email
        password = credential_value

    response = client.post(
        '/login',
        data={'email': email, 'password': password},
        follow_redirects=True,
    )
    assert expected_message.encode() in response.data


def test_logout_rejects_get_requests(client, user_factory, login_user):
    user, password = user_factory()
    login_user(user.email, password)

    response = client.get('/logout', follow_redirects=False)
    assert response.status_code == 405


def test_signup_validates_email_format(client):
    response = client.post(
        '/signup',
        data={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'invalid-email',
            'password': 'Secret123!',
            'confirm_password': 'Secret123!',
        },
        follow_redirects=True,
    )
    assert b'valid email' in response.data.lower()


def test_signup_validates_password_min_length(client):
    response = client.post(
        '/signup',
        data={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'short',
            'confirm_password': 'short',
        },
        follow_redirects=True,
    )
    assert b'at least 8 characters' in response.data


def test_signup_validates_password_mismatch(client):
    response = client.post(
        '/signup',
        data={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'Password123!',
            'confirm_password': 'Different123!',
        },
        follow_redirects=True,
    )
    assert b'do not match' in response.data


def test_login_remember_me_sets_persistent_cookie(client, user_factory):
    user, password = user_factory()
    response = client.post(
        '/login',
        data={'email': user.email, 'password': password, 'remember': 'on'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    set_cookie = response.headers.get('Set-Cookie', '')
    has_persistent = 'expires' in set_cookie.lower() or 'max-age' in set_cookie.lower()
    assert has_persistent, 'remember=on should set a persistent cookie with Expires or Max-Age'


def test_profile_page_requires_login(client):
    response = client.get('/profile', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_profile_page_shows_user_data(client, user_factory, login_user):
    user, password = user_factory(first_name='John', last_name='Doe')
    login_user(user.email, password)

    response = client.get('/profile')
    assert response.status_code == 200
    assert b'John' in response.data
    assert b'Doe' in response.data


def test_profile_update_with_wrong_password_fails(client, user_factory, login_user):
    user, password = user_factory(first_name='OldName')
    login_user(user.email, password)

    response = client.post(
        '/profile',
        data={
            'first_name': 'NewName',
            'last_name': 'Doe',
            'current_password': 'WrongPass123!',
            'new_password': '',
        },
        follow_redirects=True,
    )
    assert b'incorrect' in response.data.lower()


def test_profile_update_with_short_new_password_fails(client, user_factory, login_user):
    user, password = user_factory(first_name='OldName')
    login_user(user.email, password)

    response = client.post(
        '/profile',
        data={
            'first_name': 'NewName',
            'last_name': 'Doe',
            'current_password': password,
            'new_password': 'short',
        },
        follow_redirects=True,
    )
    assert b'at least 8 characters' in response.data


def test_profile_update_success_changes_name(client, user_factory, login_user):
    user, password = user_factory(first_name='OldName', last_name='Smith')
    login_user(user.email, password)

    response = client.post(
        '/profile',
        data={
            'first_name': 'NewName',
            'last_name': 'Smith',
            'current_password': password,
            'new_password': '',
        },
        follow_redirects=True,
    )
    assert b'successfully' in response.data

    db.session.refresh(user)
    assert user.first_name == 'NewName'


def test_profile_update_with_new_password_logs_out(client, user_factory, login_user):
    user, password = user_factory()
    login_user(user.email, password)

    response = client.post(
        '/profile',
        data={
            'first_name': 'John',
            'last_name': 'Doe',
            'current_password': password,
            'new_password': 'NewPass123!',
        },
        follow_redirects=True,
    )
    assert b'log in with your new password' in response.data


def test_delete_account_with_wrong_password_fails(client, user_factory, login_user):
    user, password = user_factory()
    login_user(user.email, password)

    response = client.post(
        '/profile/delete',
        data={'delete_password': 'WrongPass123!'},
        follow_redirects=True,
    )
    assert b'incorrect' in response.data.lower()


def test_delete_account_with_correct_password_succeeds(client, user_factory, login_user):
    user, password = user_factory()
    login_user(user.email, password)

    response = client.post(
        '/profile/delete',
        data={'delete_password': password},
        follow_redirects=True,
    )

    db.session.refresh(user)
    assert user.status == 'deleted'
    assert user.email is None


def test_login_loader_rejects_deleted_user(client, user_factory):
    user, _ = user_factory(email='loader-deleted@example.com')
    user_email = user.email
    user.status = 'deleted'
    user.deleted_at = datetime.now(timezone.utc)
    user.email = None
    db.session.commit()

    response = client.post(
        '/login',
        data={'email': user_email, 'password': 'anypass'},
        follow_redirects=True,
    )
    assert b'Invalid email or password' in response.data


def test_delete_account_requires_password(client, user_factory, login_user):
    user, password = user_factory(email='del-no-pass@example.com')
    login_user(user.email, password)

    response = client.post(
        '/profile/delete',
        data={'delete_password': ''},
        follow_redirects=True,
    )
    assert b'password is required' in response.data.lower()


def test_signup_duplicate_email_rejected(client):
    payload = {
        'first_name': 'Alice',
        'last_name': 'Doe',
        'email': 'duplicate@example.com',
        'password': 'Secret123!',
        'confirm_password': 'Secret123!',
    }

    client.post('/signup', data=payload, follow_redirects=True)
    assert User.query.filter_by(email='duplicate@example.com').count() == 1

    response = client.post('/signup', data=payload, follow_redirects=True)
    assert User.query.filter_by(email='duplicate@example.com').count() == 1
