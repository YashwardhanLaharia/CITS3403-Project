from extensions import db
from models import User


def test_set_password_creates_hash(app):
    user = User(
        email='hasher@example.com',
        first_name='Test',
        last_name='User',
    )
    user.set_password('MySecretPass123!')

    assert user.password_hash is not None
    assert user.password_hash != 'MySecretPass123!'
    assert len(user.password_hash) > 20


def test_check_password_validates_correctly(app):
    user = User(
        email='validator@example.com',
        first_name='Test',
        last_name='User',
    )
    user.set_password('CorrectPass123!')

    assert user.check_password('CorrectPass123!') is True
    assert user.check_password('WrongPass123!') is False
    assert user.check_password('') is False
    assert user.check_password(None) is False


def test_check_password_returns_false_for_empty_hash(app):
    user = User(
        email='emptyhash@example.com',
        first_name='Test',
        last_name='User',
    )
    user.password_hash = ''

    assert user.check_password('anypass') is False


def test_set_password_produces_different_hashes(app):
    user1 = User(email='diff1@example.com', first_name='A', last_name='B')
    user2 = User(email='diff2@example.com', first_name='A', last_name='B')

    user1.set_password('SamePassword123!')
    user2.set_password('SamePassword123!')

    assert user1.password_hash != user2.password_hash


def test_user_is_active_default(app):
    user = User(email='active@example.com', first_name='A', last_name='B')
    user.set_password('TempPass123!')
    db.session.add(user)
    db.session.commit()

    assert user.is_active is True
    assert user.status == 'active'


def test_user_display_name(app):
    user = User(
        email='name@example.com',
        first_name='John',
        last_name='Doe',
    )
    user.set_password('TempPass123!')
    db.session.add(user)
    db.session.commit()

    assert user.display_name == 'John Doe'


def test_user_display_name_with_deleted_status(app):
    user = User(
        email='deleted@example.com',
        first_name='John',
        last_name='Doe',
    )
    user.set_password('TempPass123!')
    user.status = 'deleted'
    db.session.add(user)
    db.session.commit()

    assert user.display_name == 'John Doe (deleted)'


def test_user_created_at_is_set_auto(app):
    user = User(
        email='created-at@example.com',
        first_name='Test',
        last_name='User',
    )
    user.set_password('TempPass123!')
    db.session.add(user)
    db.session.commit()

    assert user.created_at is not None