from datetime import date

from extensions import db
from models import Expense, ExpenseSplit, Group, Membership, User
from routes.main import _compute_group_data


def test_compute_group_data_balance_calculation(app, user_factory):
    user1, _ = user_factory(email='user1-settle@example.com')
    user2, _ = user_factory(email='user2-settle@example.com')

    group = Group(
        name='Settlement Group',
        currency='AUD',
        created_by=user1.id,
        invite_code='SETTLE01',
    )
    db.session.add(group)
    db.session.flush()

    membership1 = Membership(user_id=user1.id, group_id=group.id, role='admin')
    membership2 = Membership(user_id=user2.id, group_id=group.id, role='member')
    db.session.add(membership1)
    db.session.add(membership2)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user1.id,
        description='Dinner',
        amount=100.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 1),
    )
    db.session.add(expense)
    db.session.flush()

    db.session.add(ExpenseSplit(expense_id=expense.id, user_id=user1.id, share_amount=50.00))
    db.session.add(ExpenseSplit(expense_id=expense.id, user_id=user2.id, share_amount=50.00))
    db.session.commit()

    members_by_id = {user1.id: user1, user2.id: user2}
    expenses = Expense.query.filter_by(group_id=group.id).all()

    members, categories, transfers, total_spent = _compute_group_data(members_by_id, expenses)

    assert total_spent == 100.00

    user1_data = next(m for m in members if m['id'] == user1.id)
    user2_data = next(m for m in members if m['id'] == user2.id)

    assert user1_data['paid'] == 100.00
    assert user1_data['balance'] == 50.00

    assert user2_data['paid'] == 0.00
    assert user2_data['balance'] == -50.00


def test_compute_group_data_settlement_transfers(app, user_factory):
    user1, _ = user_factory(email='payer1@example.com')
    user2, _ = user_factory(email='payer2@example.com')

    group = Group(
        name='Transfer Group',
        currency='AUD',
        created_by=user1.id,
        invite_code='TRANSFER',
    )
    db.session.add(group)
    db.session.flush()

    membership1 = Membership(user_id=user1.id, group_id=group.id, role='admin')
    membership2 = Membership(user_id=user2.id, group_id=group.id, role='member')
    db.session.add(membership1)
    db.session.add(membership2)
    db.session.flush()

    expense = Expense(
        group_id=group.id,
        paid_by=user1.id,
        description='Groceries',
        amount=60.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 2),
    )
    db.session.add(expense)
    db.session.flush()

    db.session.add(ExpenseSplit(expense_id=expense.id, user_id=user1.id, share_amount=30.00))
    db.session.add(ExpenseSplit(expense_id=expense.id, user_id=user2.id, share_amount=30.00))
    db.session.commit()

    members_by_id = {user1.id: user1, user2.id: user2}
    expenses = Expense.query.filter_by(group_id=group.id).all()

    members, categories, transfers, total_spent = _compute_group_data(members_by_id, expenses)

    assert len(transfers) == 1
    transfer = transfers[0]

    assert transfer['from_name'] == user2.display_name
    assert transfer['to_name'] == user1.display_name
    assert transfer['amount'] == 30.00


def test_compute_group_data_zero_balance_no_transfer(app, user_factory):
    user1, _ = user_factory(email='equal1@example.com')
    user2, _ = user_factory(email='equal2@example.com')

    group = Group(
        name='Equal Group',
        currency='AUD',
        created_by=user1.id,
        invite_code='EQUALGRP',
    )
    db.session.add(group)
    db.session.flush()

    membership1 = Membership(user_id=user1.id, group_id=group.id, role='admin')
    membership2 = Membership(user_id=user2.id, group_id=group.id, role='member')
    db.session.add(membership1)
    db.session.add(membership2)
    db.session.flush()

    expense1 = Expense(
        group_id=group.id,
        paid_by=user1.id,
        description='Lunch',
        amount=40.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 3),
    )
    expense2 = Expense(
        group_id=group.id,
        paid_by=user2.id,
        description='Movie',
        amount=40.00,
        category='Entertainment',
        split_type='equal',
        date=date(2025, 1, 4),
    )
    db.session.add(expense1)
    db.session.add(expense2)
    db.session.flush()

    for exp in [expense1, expense2]:
        db.session.add(ExpenseSplit(expense_id=exp.id, user_id=user1.id, share_amount=20.00))
        db.session.add(ExpenseSplit(expense_id=exp.id, user_id=user2.id, share_amount=20.00))
    db.session.commit()

    members_by_id = {user1.id: user1, user2.id: user2}
    expenses = Expense.query.filter_by(group_id=group.id).all()

    members, categories, transfers, total_spent = _compute_group_data(members_by_id, expenses)

    assert total_spent == 80.00
    assert len(transfers) == 0


def test_compute_group_data_category_totals(app, user_factory):
    user1, _ = user_factory(email='cat1@example.com')

    group = Group(
        name='Category Group',
        currency='AUD',
        created_by=user1.id,
        invite_code='CATEGGRP',
    )
    db.session.add(group)
    db.session.flush()

    membership = Membership(user_id=user1.id, group_id=group.id, role='admin')
    db.session.add(membership)
    db.session.flush()

    expense1 = Expense(
        group_id=group.id,
        paid_by=user1.id,
        description='Pizza',
        amount=50.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 5),
    )
    expense2 = Expense(
        group_id=group.id,
        paid_by=user1.id,
        description='Taxi',
        amount=30.00,
        category='Transport',
        split_type='equal',
        date=date(2025, 1, 6),
    )
    db.session.add(expense1)
    db.session.add(expense2)
    db.session.flush()

    for exp in [expense1, expense2]:
        db.session.add(ExpenseSplit(expense_id=exp.id, user_id=user1.id, share_amount=float(exp.amount)))
    db.session.commit()

    members_by_id = {user1.id: user1}
    expenses = Expense.query.filter_by(group_id=group.id).all()

    members, categories, transfers, total_spent = _compute_group_data(members_by_id, expenses)

    assert total_spent == 80.00
    assert len(categories) == 2

    food_cat = next(c for c in categories if c['name'] == 'Food')
    assert food_cat['amount'] == 50.00

    transport_cat = next(c for c in categories if c['name'] == 'Transport')
    assert transport_cat['amount'] == 30.00