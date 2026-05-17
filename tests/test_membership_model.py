import pytest
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Group, Membership, User


def test_membership_default_role_is_member(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Test Group',
        currency='AUD',
        created_by=user.id,
        invite_code='TEST1234',
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id)
    db.session.add(membership)
    db.session.commit()

    assert membership.role == 'member'


def test_membership_can_have_admin_role(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Admin Group',
        currency='AUD',
        created_by=user.id,
        invite_code='ADMIN001',
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.commit()

    assert membership.role == 'admin'


def test_user_can_belong_to_multiple_groups(app, user_factory):
    user, _ = user_factory()

    group1 = Group(
        name='Group One',
        currency='AUD',
        created_by=user.id,
        invite_code='GROUPONE',
    )
    group2 = Group(
        name='Group Two',
        currency='USD',
        created_by=user.id,
        invite_code='GROUPTWO',
    )
    db.session.add(group1)
    db.session.add(group2)
    db.session.flush()

    membership1 = Membership(user_id=user.id, group_id=group1.id, role='admin')
    membership2 = Membership(user_id=user.id, group_id=group2.id, role='member')
    db.session.add(membership1)
    db.session.add(membership2)
    db.session.commit()

    memberships = Membership.query.filter_by(user_id=user.id).all()
    assert len(memberships) == 2


def test_duplicate_membership_raises_integrity_error(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Single Group',
        currency='AUD',
        created_by=user.id,
        invite_code='SINGLE01',
    )
    db.session.add(group)
    db.session.flush()

    membership1 = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership1)
    db.session.commit()

    membership2 = Membership(user_id=user.id, group_id=group.id, role='member')
    db.session.add(membership2)

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_membership_joined_at_is_set(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Timestamp Group',
        currency='AUD',
        created_by=user.id,
        invite_code='TIME001',
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id)
    db.session.add(membership)
    db.session.commit()

    assert membership.joined_at is not None
