import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Expense, ExpenseSplit, Group, Membership, User


def test_expense_split_type_default_is_equal(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Default Split Group',
        currency='AUD',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Test Expense',
        amount=50.00,
        category='Food',
    )
    db.session.add(expense)
    db.session.commit()

    assert expense.split_type == 'equal'


def test_expense_split_type_can_be_custom(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Custom Split Group',
        currency='AUD',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Custom Split Expense',
        amount=100.00,
        category='Entertainment',
        split_type='custom',
    )
    db.session.add(expense)
    db.session.commit()

    assert expense.split_type == 'custom'


def test_expense_split_is_paid_default_is_false(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Paid Status Group',
        currency='AUD',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Test',
        amount=25.00,
        category='Other',
    )
    db.session.add(expense)
    db.session.flush()

    split = ExpenseSplit(
        expense_id=expense.id,
        user_id=user.id,
        share_amount=25.00,
    )
    db.session.add(split)
    db.session.commit()

    assert split.is_paid is False


def test_expense_split_is_paid_can_be_true(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Mark Paid Group',
        currency='AUD',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Settled',
        amount=30.00,
        category='Food',
    )
    db.session.add(expense)
    db.session.flush()

    split = ExpenseSplit(
        expense_id=expense.id,
        user_id=user.id,
        share_amount=30.00,
        is_paid=True,
    )
    db.session.add(split)
    db.session.commit()

    assert split.is_paid is True


def test_expense_split_unique_constraint_prevents_duplicate(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Unique Split Group',
        currency='AUD',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Test Unique',
        amount=40.00,
        category='Food',
    )
    db.session.add(expense)
    db.session.flush()

    split1 = ExpenseSplit(
        expense_id=expense.id,
        user_id=user.id,
        share_amount=40.00,
    )
    db.session.add(split1)
    db.session.commit()

    split2 = ExpenseSplit(
        expense_id=expense.id,
        user_id=user.id,
        share_amount=20.00,
    )
    db.session.add(split2)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_expense_amount_stored_as_decimal(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Decimal Group',
        currency='AUD',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Precise Amount',
        amount=33.33,
        category='Food',
    )
    db.session.add(expense)
    db.session.commit()

    fetched = db.session.get(Expense, expense.id)
    assert isinstance(fetched.amount, Decimal)
    assert fetched.amount == Decimal('33.33')


def test_expense_split_share_amount_stored_as_decimal(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Share Decimal Group',
        currency='AUD',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Split Amount',
        amount=50.00,
        category='Food',
    )
    db.session.add(expense)
    db.session.flush()

    split = ExpenseSplit(
        expense_id=expense.id,
        user_id=user.id,
        share_amount=16.67,
    )
    db.session.add(split)
    db.session.commit()

    fetched = db.session.get(ExpenseSplit, split.id)
    assert isinstance(fetched.share_amount, Decimal)
    assert fetched.share_amount == Decimal('16.67')


def test_expense_default_date_is_today(app, user_factory):
    user, _ = user_factory()
    group = Group(
        name='Date Default Group',
        currency='AUD',
        created_by=user.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user.id,
        description='Default Date',
        amount=20.00,
        category='Food',
    )
    db.session.add(expense)
    db.session.commit()

    today = date.today()
    assert expense.date == today
