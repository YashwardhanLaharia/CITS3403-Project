import string
from extensions import db
from models import Group, User


def test_generate_invite_code_returns_string(app):
    code = Group.generate_invite_code()

    assert isinstance(code, str)
    assert len(code) == 8


def test_generate_invite_code_uses_uppercase_and_digits(app):
    code = Group.generate_invite_code()

    assert all(c in string.ascii_uppercase + string.digits for c in code)


def test_generate_invite_code_produces_unique_codes(app):
    codes = [Group.generate_invite_code() for _ in range(100)]

    assert len(set(codes)) == 100


def test_generate_invite_code_avoids_existing_codes(app):
    user = User(email='code-test@example.com', first_name='T', last_name='U')
    user.set_password('TempPass123!')
    db.session.add(user)
    db.session.commit()

    group = Group(
        name='Existing Group',
        currency='AUD',
        created_by=user.id,
        invite_code='EXISTING',
    )
    db.session.add(group)
    db.session.commit()

    code = Group.generate_invite_code()

    assert code != 'EXISTING'


def test_group_creation_with_custom_invite_code(app, user_factory):
    user, _ = user_factory()

    group = Group(
        name='Custom Code Group',
        currency='USD',
        created_by=user.id,
        invite_code='CUSTOM01',
    )
    db.session.add(group)
    db.session.commit()

    assert group.invite_code == 'CUSTOM01'
    fetched = db.session.get(Group, group.id)
    assert fetched.invite_code == 'CUSTOM01'


def test_group_default_currency_is_aud(app, user_factory):
    user, _ = user_factory()

    group = Group(
        name='Default Currency',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.commit()

    assert group.currency == 'AUD'


def test_group_created_at_is_set_auto(app, user_factory):
    user, _ = user_factory()

    group = Group(
        name='Timestamp Test',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.commit()

    assert group.created_at is not None


def test_group_start_and_end_date_can_be_set(app, user_factory):
    from datetime import date
    user, _ = user_factory()

    group = Group(
        name='Date Range Group',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    db.session.add(group)
    db.session.commit()

    assert group.start_date == date(2025, 1, 1)
    assert group.end_date == date(2025, 12, 31)
