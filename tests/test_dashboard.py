from datetime import datetime, timezone

from extensions import db as _db
from models import Expense, ExpenseSplit, Membership


def _create_expense(group, payer_id, description, amount, category, shares):
    expense = Expense(
        group_id=group.id,
        paid_by=payer_id,
        description=description,
        amount=amount,
        category=category,
        split_type='custom',
    )
    _db.session.add(expense)
    _db.session.flush()

    for user_id, share in shares.items():
        _db.session.add(ExpenseSplit(expense_id=expense.id, user_id=user_id, share_amount=share))

    _db.session.commit()
    return expense


def test_dashboard_summary_displays_balances(
    client, user_factory, group_factory, login_user
):
    admin, password = user_factory(email='admin-dashboard@example.com')
    group = group_factory(creator=admin)
    member, _ = user_factory(email='member-dashboard@example.com')
    _db.session.add(Membership(user_id=member.id, group_id=group.id, role='member'))
    _db.session.commit()

    _create_expense(
        group,
        payer_id=admin.id,
        description='Lunch',
        amount=100.00,
        category='Food',
        shares={admin.id: 50.00, member.id: 50.00},
    )
    _create_expense(
        group,
        payer_id=member.id,
        description='Train tickets',
        amount=60.00,
        category='Transport',
        shares={admin.id: 30.00, member.id: 30.00},
    )

    login_user(admin.email, password)
    response = client.get(f'/groups/{group.id}')

    assert b'Member Balances' in response.data
    assert b'Lunch' in response.data
    assert b'Train tickets' in response.data
    assert b'Settlement Preview' in response.data
    assert b'Food' in response.data
    assert b'Transport' in response.data
    # the group invite code should appear on the dashboard
    assert group.invite_code.encode() in response.data


def test_dashboard_renders_with_mixed_member_statuses(
    client, user_factory, group_factory, login_user
):
    admin, password = user_factory(email='admin-del-member@example.com')
    group = group_factory(creator=admin)
    deleted_member, _ = user_factory(email='deleted-member@example.com')
    active_member, _ = user_factory(email='active-member@example.com')

    _db.session.add(Membership(user_id=deleted_member.id, group_id=group.id, role='member'))
    _db.session.add(Membership(user_id=active_member.id, group_id=group.id, role='member'))
    _db.session.commit()

    deleted_member.status = 'deleted'
    deleted_member.deleted_at = datetime.now(timezone.utc)
    _db.session.commit()

    login_user(admin.email, password)
    response = client.get(f'/groups/{group.id}')

    assert response.status_code == 200
    assert b'Member Balances' in response.data
