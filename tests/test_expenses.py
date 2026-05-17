import json
from decimal import Decimal

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
    custom_splits = {split.user_id: split.share_amount for split in splits_query}
    assert custom_splits[admin.id] == Decimal('90.00')
    assert custom_splits[extra_user.id] == Decimal('60.00')


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


def test_add_expense_requires_login(client, user_factory, group_factory):
    admin, _ = user_factory(email='admin-login@example.com')
    group = group_factory(creator=admin)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Test',
            'amount': '50.00',
            'category': 'Food',
        },
        follow_redirects=False,
    )
    assert response.status_code == 302


def test_add_expense_returns_404_for_non_member(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-404@example.com')
    group = group_factory(creator=admin)
    other_user, other_password = user_factory(email='other-exp@example.com')
    login_user(other_user.email, other_password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Should fail',
            'amount': '50.00',
            'category': 'Food',
        },
    )
    assert response.status_code == 404


def test_add_expense_missing_description_validation(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-desc@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': '',
            'amount': '50.00',
            'category': 'Food',
        },
        follow_redirects=True,
    )
    assert b'description' in response.data.lower()
    assert Expense.query.filter_by(group_id=group.id, description='').first() is None


def test_add_expense_missing_amount_validation(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-amt@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Test Expense',
            'amount': '',
            'category': 'Food',
        },
        follow_redirects=True,
    )
    assert b'amount' in response.data.lower()
    assert Expense.query.filter_by(group_id=group.id, description='Test Expense').first() is None


def test_add_expense_invalid_amount_negative(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-neg@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Negative',
            'amount': '-50.00',
            'category': 'Food',
        },
        follow_redirects=True,
    )
    assert b'positive' in response.data.lower()
    assert Expense.query.filter_by(group_id=group.id, description='Negative').first() is None


def test_add_expense_invalid_amount_zero(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-zero@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Zero',
            'amount': '0',
            'category': 'Food',
        },
        follow_redirects=True,
    )
    assert b'positive' in response.data.lower()
    assert Expense.query.filter_by(group_id=group.id, description='Zero').first() is None


def test_add_expense_non_numeric_amount(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-nonnum@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Non-numeric',
            'amount': 'abc',
            'category': 'Food',
        },
        follow_redirects=True,
    )
    assert b'valid number' in response.data.lower()
    assert Expense.query.filter_by(description='Non-numeric').first() is None


def test_add_expense_invalid_category(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-cat@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Test',
            'amount': '50.00',
            'category': 'InvalidCategory',
        },
        follow_redirects=True,
    )
    assert b'valid category' in response.data.lower()
    assert Expense.query.filter_by(description='Test').first() is None


def test_add_expense_invalid_date_format(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-date@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Test',
            'amount': '50.00',
            'category': 'Food',
            'expense_date': 'invalid-date',
        },
        follow_redirects=True,
    )
    assert b'date' in response.data.lower()
    assert Expense.query.filter_by(description='Test').count() == 0


def test_add_expense_custom_split_negative_amount(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-neg-split@example.com')
    group = group_factory(creator=admin)
    extra_user, _ = user_factory(email='member-neg-split@example.com')
    _db.session.add(Membership(user_id=extra_user.id, group_id=group.id, role='member'))
    _db.session.commit()
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Negative Split',
            'amount': '60.00',
            'category': 'Food',
            'split_type': 'custom',
            f'split_amount_{admin.id}': '70.00',
            f'split_amount_{extra_user.id}': '-10.00',
        },
        follow_redirects=True,
    )
    assert b'negative' in response.data.lower()
    assert Expense.query.filter_by(description='Negative Split').first() is None


def test_add_expense_creates_expense_with_correct_fields(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-fields@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Taxi',
            'amount': '25.00',
            'category': 'Transport',
            'expense_date': '2025-06-15',
            'split_type': 'equal',
        },
        follow_redirects=True,
    )

    expense = Expense.query.filter_by(description='Taxi').first()
    assert expense is not None
    assert expense.amount == Decimal('25.00')
    assert expense.category == 'Transport'
    assert expense.paid_by == admin.id
    assert expense.group_id == group.id


def test_add_expense_custom_split_zero_total(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-zero-split@example.com')
    group = group_factory(creator=admin)
    extra_user, _ = user_factory(email='member-zero-split@example.com')
    _db.session.add(Membership(user_id=extra_user.id, group_id=group.id, role='member'))
    _db.session.commit()
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Zero Split Total',
            'amount': '50.00',
            'category': 'Food',
            'split_type': 'custom',
            f'split_amount_{admin.id}': '0',
            f'split_amount_{extra_user.id}': '0',
        },
        follow_redirects=True,
    )
    assert b'greater than zero' in response.data.lower()
    assert Expense.query.filter_by(description='Zero Split Total').first() is None


def test_add_expense_ajax_validation_error_returns_json(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-ajax-err@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': '',
            'amount': '50.00',
            'category': 'Food',
        },
        headers={'X-Requested-With': 'XMLHttpRequest'},
    )

    assert response.status_code == 400
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'errors' in data


def test_add_expense_ajax_success_returns_json(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-ajax-succ@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Ajax Success',
            'amount': '30.00',
            'category': 'Food',
            'split_type': 'equal',
        },
        headers={'X-Requested-With': 'XMLHttpRequest'},
    )

    assert response.status_code == 200
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert data['success'] is True
