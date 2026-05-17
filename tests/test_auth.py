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
