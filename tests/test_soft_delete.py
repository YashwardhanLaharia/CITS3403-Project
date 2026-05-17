from datetime import datetime

from extensions import db
from models import User, Group, Membership, Expense, ExpenseSplit


def test_soft_delete_sets_status_and_timestamp(app, user_factory):
    user, _ = user_factory()
    user.status = 'deleted'
    user.deleted_at = datetime.utcnow()
    user.email = None
    db.session.commit()

    fetched = db.session.get(User, user.id)
    assert fetched.status == 'deleted'
    assert fetched.deleted_at is not None
    assert fetched.email is None


def test_soft_deleted_user_is_not_active(app, user_factory):
    user, _ = user_factory()
    assert user.is_active is True

    user.status = 'deleted'
    db.session.commit()

    assert user.is_active is False


def test_soft_deleted_user_display_name_shows_badge(app, user_factory):
    user, _ = user_factory(first_name='Alice', last_name='Smith')
    assert user.display_name == 'Alice Smith'

    user.status = 'deleted'
    db.session.commit()

    assert user.display_name == 'Alice Smith (deleted)'


def test_soft_deleted_user_cannot_log_in(client, user_factory):
    user, password = user_factory()
    user.status = 'deleted'
    db.session.commit()

    response = client.post('/login', data={
        'email': user.email,
        'password': password,
    }, follow_redirects=True)

    assert b'Invalid email or password' in response.data


def test_memberships_remain_after_soft_delete(app, user_factory, group_factory):
    user, _ = user_factory()
    group = group_factory(creator=user)

    user.status = 'deleted'
    db.session.commit()

    membership = Membership.query.filter_by(user_id=user.id).first()
    assert membership is not None


def test_expenses_remain_after_soft_delete(app, user_factory, group_factory):
    user, _ = user_factory()
    group = group_factory(creator=user)

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Groceries',
        amount=50.00,
        category='Food',
    )
    db.session.add(expense)
    db.session.commit()

    user.status = 'deleted'
    db.session.commit()

    fetched = Expense.query.filter_by(paid_by=user.id).first()
    assert fetched is not None
    assert fetched.description == 'Groceries'


def test_expense_splits_remain_after_soft_delete(app, user_factory, group_factory):
    creator, _ = user_factory()
    member, _ = user_factory()
    group = group_factory(creator=creator)

    db.session.add(Membership(user_id=member.id, group_id=group.id, role='member'))
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=creator.id,
        description='Dinner',
        amount=40.00,
        category='Food',
    )
    db.session.add(expense)
    db.session.flush()

    split = ExpenseSplit(expense_id=expense.id, user_id=member.id, share_amount=20.00)
    db.session.add(split)
    db.session.commit()

    member.status = 'deleted'
    db.session.commit()

    fetched = ExpenseSplit.query.filter_by(user_id=member.id).first()
    assert fetched is not None
    assert float(fetched.share_amount) == 20.00


def test_delete_account_route(client, user_factory, login_user):
    user, password = user_factory()
    login_user(user.email, password)

    response = client.post('/profile/delete', data={
        'delete_password': password,
    }, follow_redirects=True)

    assert b'deleted' in response.data or b'log' in response.data.lower()

    fetched = db.session.get(User, user.id)
    assert fetched.status == 'deleted'
    assert fetched.email is None
