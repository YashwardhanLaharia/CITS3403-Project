import uuid

import pytest
from app import create_app
from extensions import db as _db
from models import Group, Membership, User


@pytest.fixture
def app():
    app = create_app('testing')

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _build_unique_email(prefix='user'):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def user_factory():
    def _create_user(**kwargs):
        defaults = {
            'email': _build_unique_email('test'),
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'Secret123!'
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        user = User(**defaults)
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        return user, password

    return _create_user


@pytest.fixture
def group_factory(user_factory):
    def _create_group(creator=None, **kwargs):
        if creator is None:
            creator, _ = user_factory()

        group = Group(
            name=kwargs.get('name', 'Test Group'),
            currency=kwargs.get('currency', 'AUD'),
            created_by=creator.id,
            invite_code=Group.generate_invite_code(),
        )
        _db.session.add(group)
        _db.session.flush()
        membership = Membership(user_id=creator.id, group_id=group.id, role=kwargs.get('role', 'admin'))
        _db.session.add(membership)
        _db.session.commit()
        return group

    return _create_group


@pytest.fixture
def login_user(client):
    def _login(email, password):
        return client.post(
            '/login',
            data={'email': email, 'password': password},
            follow_redirects=True,
        )

    return _login
