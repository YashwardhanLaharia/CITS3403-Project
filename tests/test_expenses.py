from extensions import db as _db
from models import Expense, ExpenseSplit, Membership


def test_add_equal_expense_creates_splits(
    client, user_factory, group_factory, login_user
):
    admin, password = user_factory(email='admin-expense@example.com')
    group = group_factory(creator=admin)
    extra_user, _ = user_factory(email='member-expense@example.com')
    membership = Membership(user_id=extra_user.id, group_id=group.id, role='member')
    _db.session.add(membership)
    _db.session.commit()

    login_user(admin.email, password)

    client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Lunch',
            'amount': '100.00',
            'category': 'Food',
            'expense_date': '2025-01-01',
            'split_type': 'equal',
        },
        follow_redirects=True,
    )

    expense = Expense.query.filter_by(description='Lunch').first()
    assert expense is not None
    splits = ExpenseSplit.query.filter_by(expense_id=expense.id).all()
    assert len(splits) == 2


def test_add_custom_splits_respects_amounts(
    client, user_factory, group_factory, login_user
):
    admin, password = user_factory(email='admin-custom@example.com')
    group = group_factory(creator=admin)
    extra_user, _ = user_factory(email='member-custom@example.com')
    _db.session.add(Membership(user_id=extra_user.id, group_id=group.id, role='member'))
    _db.session.commit()

    login_user(admin.email, password)

    client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Dinner',
            'amount': '150.00',
            'category': 'Entertainment',
            'expense_date': '2025-01-02',
            'split_type': 'custom',
            f'split_amount_{admin.id}': '90.00',
            f'split_amount_{extra_user.id}': '60.00',
        },
        follow_redirects=True,
    )

    expense = Expense.query.filter_by(description='Dinner').first()
    assert expense is not None
    splits_query = ExpenseSplit.query.filter_by(expense_id=expense.id)
    custom_splits = {split.user_id: float(split.share_amount) for split in splits_query}
    assert custom_splits[admin.id] == 90.0
    assert custom_splits[extra_user.id] == 60.0


def test_custom_split_validation_fails_when_totals_mismatch(
    client, user_factory, group_factory, login_user
):
    admin, password = user_factory(email='admin-mismatch@example.com')
    group = group_factory(creator=admin)
    extra_user, _ = user_factory(email='member-mismatch@example.com')
    _db.session.add(Membership(user_id=extra_user.id, group_id=group.id, role='member'))
    _db.session.commit()

    login_user(admin.email, password)

    client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Broken Split',
            'amount': '60.00',
            'category': 'Other',
            'expense_date': '2025-01-03',
            'split_type': 'custom',
            f'split_amount_{admin.id}': '30.00',
            f'split_amount_{extra_user.id}': '20.00',
        },
        follow_redirects=True,
    )

    assert Expense.query.filter_by(description='Broken Split').first() is None
