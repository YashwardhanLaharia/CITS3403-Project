from datetime import datetime, timezone

from models import User


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


def test_login_requires_valid_credentials(client, user_factory):
    user, _ = user_factory()

    response = client.post(
        '/login',
        data={'email': user.email, 'password': 'wrongpass'},
        follow_redirects=True,
    )
    assert b'Invalid email or password.' in response.data


def test_index_requires_login(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_login_with_nonexistent_email(client):
    response = client.post(
        '/login',
        data={'email': 'nonexistent@example.com', 'password': 'anypass'},
        follow_redirects=True,
    )
    assert b'Invalid email or password.' in response.data


def test_login_with_wrong_password(client, user_factory):
    user, _ = user_factory()
    response = client.post(
        '/login',
        data={'email': user.email, 'password': 'WrongPassword123!'},
        follow_redirects=True,
    )
    assert b'Invalid email or password.' in response.data


def test_login_with_deleted_account(client, user_factory):
    user, password = user_factory()
    user_email = user.email
    from extensions import db
    user.status = 'deleted'
    user.deleted_at = datetime.now(timezone.utc)
    user.email = None
    db.session.commit()

    response = client.post(
        '/login',
        data={'email': user_email, 'password': password},
        follow_redirects=True,
    )
    assert b'Invalid email or password.' in response.data


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


def test_login_remember_me_option(client, user_factory):
    user, password = user_factory()
    response = client.post(
        '/login',
        data={'email': user.email, 'password': password, 'remember': 'on'},
        follow_redirects=True,
    )
    assert 'Set-Cookie' in response.headers
    session_cookie = response.headers.get('Set-Cookie', '')
    assert 'session' in session_cookie.lower()


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

    from extensions import db
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

    from extensions import db
    db.session.refresh(user)
    assert user.status == 'deleted'
    assert user.email is None
