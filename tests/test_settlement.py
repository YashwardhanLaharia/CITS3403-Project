from datetime import date

from extensions import db
from models import Expense, ExpenseSplit, Group, Membership
from routes.main import _compute_group_data


def test_compute_group_data_balance_calculation(app, user_factory):
    user1, _ = user_factory(email='user1-settle@example.com')
    user2, _ = user_factory(email='user2-settle@example.com')

    group = Group(
        name='Settlement Group',
        currency='AUD',
        created_by=user1.id,
        invite_code=Group.generate_invite_code(),
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
        invite_code=Group.generate_invite_code(),
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
        invite_code=Group.generate_invite_code(),
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
        invite_code=Group.generate_invite_code(),
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


def test_compute_group_data_empty_group(app, user_factory):
    user1, _ = user_factory(email='empty1@example.com')

    group = Group(
        name='Empty Group',
        currency='AUD',
        created_by=user1.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.commit()

    members_by_id = {user1.id: user1}
    expenses = Expense.query.filter_by(group_id=group.id).all()

    members, categories, transfers, total_spent = _compute_group_data(members_by_id, expenses)

    assert total_spent == 0.00
    assert len(categories) == 0
    assert len(transfers) == 0


def test_compute_group_data_three_member_settlement(app, user_factory):
    user1, _ = user_factory(email='payer3a@example.com')
    user2, _ = user_factory(email='payer3b@example.com')
    user3, _ = user_factory(email='payer3c@example.com')

    group = Group(
        name='Three Member Group',
        currency='AUD',
        created_by=user1.id,
        invite_code=Group.generate_invite_code(),
    )
    db.session.add(group)
    db.session.flush()

    db.session.add(Membership(user_id=user1.id, group_id=group.id, role='admin'))
    db.session.add(Membership(user_id=user2.id, group_id=group.id, role='member'))
    db.session.add(Membership(user_id=user3.id, group_id=group.id, role='member'))
    db.session.commit()

    expense = Expense(
        group_id=group.id,
        paid_by=user1.id,
        description='Group Dinner',
        amount=90.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 10),
    )
    db.session.add(expense)
    db.session.flush()

    db.session.add(ExpenseSplit(expense_id=expense.id, user_id=user1.id, share_amount=30.00))
    db.session.add(ExpenseSplit(expense_id=expense.id, user_id=user2.id, share_amount=30.00))
    db.session.add(ExpenseSplit(expense_id=expense.id, user_id=user3.id, share_amount=30.00))
    db.session.commit()

    members_by_id = {user1.id: user1, user2.id: user2, user3.id: user3}
    expenses = Expense.query.filter_by(group_id=group.id).all()

    members, categories, transfers, total_spent = _compute_group_data(members_by_id, expenses)

    assert total_spent == 90.00
    assert len(transfers) == 2

    u1_data = next(m for m in members if m['id'] == user1.id)
    u2_data = next(m for m in members if m['id'] == user2.id)
    u3_data = next(m for m in members if m['id'] == user3.id)

    assert u1_data['balance'] == 60.00
    assert u2_data['balance'] == -30.00
    assert u3_data['balance'] == -30.00


def test_settle_selective_splits(client, user_factory, group_factory, login_user):
    debtor, _ = user_factory(email='debtor-sel@example.com')
    creditor, _ = user_factory(email='creditor-sel@example.com')

    admin, password = user_factory(email='admin-sel@example.com')
    group = group_factory(creator=admin)

    db.session.add(Membership(user_id=debtor.id, group_id=group.id, role='member'))
    db.session.add(Membership(user_id=creditor.id, group_id=group.id, role='member'))
    db.session.commit()

    login_user(debtor.email, password)

    expense1 = Expense(
        group_id=group.id,
        paid_by=creditor.id,
        description='Dinner',
        amount=50.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 1),
    )
    db.session.add(expense1)
    db.session.flush()

    expense2 = Expense(
        group_id=group.id,
        paid_by=creditor.id,
        description='Lunch',
        amount=30.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 2),
    )
    db.session.add(expense2)
    db.session.flush()

    split1 = ExpenseSplit(expense_id=expense1.id, user_id=debtor.id, share_amount=25.00)
    split2 = ExpenseSplit(expense_id=expense2.id, user_id=debtor.id, share_amount=15.00)
    db.session.add(split1)
    db.session.add(split2)
    db.session.commit()

    client.post(
        f'/groups/{group.id}/settle',
        data={
            'debtor_id': debtor.id,
            'creditor_id': creditor.id,
            'split_ids': str(split1.id),
        },
        follow_redirects=True,
    )

    db.session.expire_all()
    split1_refresh = ExpenseSplit.query.get(split1.id)
    split2_refresh = ExpenseSplit.query.get(split2.id)
    assert split1_refresh.is_paid is True
    assert split2_refresh.is_paid is False


def test_settle_rejects_non_debtor(client, user_factory, group_factory, login_user):
    debtor, _ = user_factory(email='debtor-auth@example.com')
    creditor, _ = user_factory(email='creditor-auth@example.com')
    other_user, other_password = user_factory(email='other-auth@example.com')
    admin, _ = user_factory(email='admin-auth@example.com')

    group = group_factory(creator=admin)
    db.session.add(Membership(user_id=debtor.id, group_id=group.id, role='member'))
    db.session.add(Membership(user_id=creditor.id, group_id=group.id, role='member'))
    db.session.add(Membership(user_id=other_user.id, group_id=group.id, role='member'))
    db.session.commit()

    expense = Expense(
        group_id=group.id,
        paid_by=creditor.id,
        description='Dinner',
        amount=50.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 1),
    )
    db.session.add(expense)
    db.session.flush()

    split = ExpenseSplit(expense_id=expense.id, user_id=debtor.id, share_amount=25.00)
    db.session.add(split)
    db.session.commit()

    login_user(other_user.email, other_password)

    response = client.post(
        f'/groups/{group.id}/settle',
        data={
            'debtor_id': debtor.id,
            'creditor_id': creditor.id,
        },
        follow_redirects=True,
    )

    assert b'You can only settle your own debts' in response.data


def test_settle_cross_debts_nets_correctly(client, user_factory, group_factory, login_user):
    # bob owes alice $10 + $30 = $40 total
    # alice owes bob $25
    # net cash_due = $40 - $25 = $15
    # sorted splits: [$10, $30] — $10 is fully covered, $30 is not
    alice, _ = user_factory(email='alice-cross@example.com')
    bob, bob_password = user_factory(email='bob-cross@example.com')

    admin, _ = user_factory(email='admin-cross@example.com')
    group = group_factory(creator=admin)

    db.session.add(Membership(user_id=alice.id, group_id=group.id, role='member'))
    db.session.add(Membership(user_id=bob.id, group_id=group.id, role='member'))
    db.session.commit()

    expense1 = Expense(
        group_id=group.id, paid_by=bob.id, description='Bob paid',
        amount=50.00, category='Food', split_type='equal', date=date(2025, 1, 1),
    )
    db.session.add(expense1)
    expense2 = Expense(
        group_id=group.id, paid_by=alice.id, description='Alice paid A',
        amount=20.00, category='Food', split_type='equal', date=date(2025, 1, 2),
    )
    db.session.add(expense2)
    expense3 = Expense(
        group_id=group.id, paid_by=alice.id, description='Alice paid B',
        amount=60.00, category='Food', split_type='equal', date=date(2025, 1, 3),
    )
    db.session.add(expense3)
    db.session.flush()

    alice_owes_bob = ExpenseSplit(expense_id=expense1.id, user_id=alice.id, share_amount=25.00)
    bob_owes_alice_small = ExpenseSplit(expense_id=expense2.id, user_id=bob.id, share_amount=10.00)
    bob_owes_alice_large = ExpenseSplit(expense_id=expense3.id, user_id=bob.id, share_amount=30.00)
    db.session.add(alice_owes_bob)
    db.session.add(bob_owes_alice_small)
    db.session.add(bob_owes_alice_large)
    db.session.commit()

    login_user(bob.email, bob_password)

    client.post(
        f'/groups/{group.id}/settle',
        data={'debtor_id': bob.id, 'creditor_id': alice.id, 'split_ids': ''},
        follow_redirects=True,
    )

    db.session.expire_all()

    assert ExpenseSplit.query.get(alice_owes_bob.id).is_paid is True      # reciprocal cleared
    assert ExpenseSplit.query.get(bob_owes_alice_small.id).is_paid is True  # $10 covered by $15 net
    assert ExpenseSplit.query.get(bob_owes_alice_large.id).is_paid is False  # $30 not covered by remaining $5


def test_settle_partial_cross_debt(client, user_factory, group_factory, login_user):
    alice, _ = user_factory(email='alice-partial@example.com')
    bob, bob_password = user_factory(email='bob-partial@example.com')

    admin, _ = user_factory(email='admin-partial@example.com')
    group = group_factory(creator=admin)

    db.session.add(Membership(user_id=alice.id, group_id=group.id, role='member'))
    db.session.add(Membership(user_id=bob.id, group_id=group.id, role='member'))
    db.session.commit()

    expense1 = Expense(
        group_id=group.id,
        paid_by=bob.id,
        description='Bob paid $100',
        amount=100.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 1),
    )
    db.session.add(expense1)
    db.session.flush()

    expense2 = Expense(
        group_id=group.id,
        paid_by=alice.id,
        description='Alice paid $50',
        amount=50.00,
        category='Food',
        split_type='equal',
        date=date(2025, 1, 2),
    )
    db.session.add(expense2)
    db.session.flush()

    bob_owes_alice = ExpenseSplit(expense_id=expense2.id, user_id=bob.id, share_amount=50.00)
    alice_owes_bob = ExpenseSplit(expense_id=expense1.id, user_id=alice.id, share_amount=25.00)
    db.session.add(bob_owes_alice)
    db.session.add(alice_owes_bob)
    db.session.commit()

    login_user(bob.email, bob_password)

    client.post(
        f'/groups/{group.id}/settle',
        data={
            'debtor_id': bob.id,
            'creditor_id': alice.id,
            'split_ids': '',
        },
        follow_redirects=True,
    )

    db.session.expire_all()

    bob_owes_alice_refresh = ExpenseSplit.query.get(bob_owes_alice.id)
    alice_owes_bob_refresh = ExpenseSplit.query.get(alice_owes_bob.id)

    assert bob_owes_alice_refresh.is_paid is False  # $50 not fully covered by $25 cash remainder
    assert alice_owes_bob_refresh.is_paid is True   # reciprocal offset applied


def test_settle_reciprocal_larger_than_net(client, user_factory, group_factory, login_user):
    # Bob owes Alice $10, Alice owes Bob $50.
    # The reciprocal ($50) exceeds debtor_total ($10) so it must NOT be marked paid.
    # cash_due = max(10 - 0, 0) = 10, which covers Bob's $10 split fully.
    alice, _ = user_factory(email='alice-recip@example.com')
    bob, bob_password = user_factory(email='bob-recip@example.com')

    admin, _ = user_factory(email='admin-recip@example.com')
    group = group_factory(creator=admin)

    db.session.add(Membership(user_id=alice.id, group_id=group.id, role='member'))
    db.session.add(Membership(user_id=bob.id, group_id=group.id, role='member'))
    db.session.commit()

    expense1 = Expense(
        group_id=group.id, paid_by=bob.id, description='Bob paid big',
        amount=100.00, category='Food', split_type='equal', date=date(2025, 1, 1),
    )
    db.session.add(expense1)
    expense2 = Expense(
        group_id=group.id, paid_by=alice.id, description='Alice paid small',
        amount=20.00, category='Food', split_type='equal', date=date(2025, 1, 2),
    )
    db.session.add(expense2)
    db.session.flush()

    alice_owes_bob = ExpenseSplit(expense_id=expense1.id, user_id=alice.id, share_amount=50.00)
    bob_owes_alice = ExpenseSplit(expense_id=expense2.id, user_id=bob.id, share_amount=10.00)
    db.session.add(alice_owes_bob)
    db.session.add(bob_owes_alice)
    db.session.commit()

    login_user(bob.email, bob_password)

    client.post(
        f'/groups/{group.id}/settle',
        data={'debtor_id': bob.id, 'creditor_id': alice.id, 'split_ids': ''},
        follow_redirects=True,
    )

    db.session.expire_all()

    assert ExpenseSplit.query.get(bob_owes_alice.id).is_paid is True   # $10 fully covered by cash_due
    assert ExpenseSplit.query.get(alice_owes_bob.id).is_paid is False  # $50 > debtor_total $10, not marked
