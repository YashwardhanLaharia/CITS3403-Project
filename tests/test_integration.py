import json

from extensions import db as _db
from models import Expense, ExpenseSplit, Group, Membership


def test_full_user_flow_signup_to_dashboard(client):
    response = client.post(
        '/signup',
        data={
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice-integration@example.com',
            'password': 'SecretPass123!',
            'confirm_password': 'SecretPass123!',
        },
        follow_redirects=True,
    )
    assert b'Registration successful' in response.data

    response = client.post(
        '/login',
        data={'email': 'alice-integration@example.com', 'password': 'SecretPass123!'},
        follow_redirects=True,
    )
    assert b'Welcome back' in response.data

    response = client.post(
        '/groups/create',
        data={'group_name': 'Trip to Bali', 'currency': 'USD'},
        follow_redirects=True,
    )
    assert b'Trip to Bali' in response.data

    group = Group.query.filter_by(name='Trip to Bali').first()
    assert group is not None

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Flight tickets',
            'amount': '500.00',
            'category': 'Transport',
            'expense_date': '2025-06-01',
            'split_type': 'equal',
        },
        follow_redirects=True,
    )
    assert b'Flight tickets' in response.data


def test_multiple_expenses_from_different_payers(client, user_factory, group_factory, login_user):
    payer1, password1 = user_factory(email='payer1-int@example.com')
    payer2, password2 = user_factory(email='payer2-int@example.com')
    group = group_factory(creator=payer1)

    _db.session.add(Membership(user_id=payer2.id, group_id=group.id, role='member'))
    _db.session.commit()

    login_user(payer1.email, password1)
    client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Dinner',
            'amount': '80.00',
            'category': 'Food',
            'split_type': 'equal',
        },
        follow_redirects=True,
    )

    login_user(payer2.email, password2)
    client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Hotel',
            'amount': '200.00',
            'category': 'Accommodation',
            'split_type': 'equal',
        },
        follow_redirects=True,
    )

    expenses = Expense.query.filter_by(group_id=group.id).all()
    assert len(expenses) == 2

    total = sum(float(e.amount) for e in expenses)
    assert total == 280.00


def test_group_with_three_members_complex_settlement(client, user_factory, group_factory, login_user):
    admin, admin_pass = user_factory(email='admin-3members@example.com')
    member1, member1_pass = user_factory(email='member1-3@example.com')
    member2, member2_pass = user_factory(email='member2-3@example.com')

    group = group_factory(creator=admin)
    _db.session.add(Membership(user_id=member1.id, group_id=group.id, role='member'))
    _db.session.add(Membership(user_id=member2.id, group_id=group.id, role='member'))
    _db.session.commit()

    login_user(admin.email, admin_pass)
    client.post(
        f'/groups/{group.id}/expenses/add',
        data={'description': 'Dinner', 'amount': '90.00', 'category': 'Food', 'split_type': 'equal'},
    )

    login_user(member1.email, member1_pass)
    client.post(
        f'/groups/{group.id}/expenses/add',
        data={'description': 'Lunch', 'amount': '60.00', 'category': 'Food', 'split_type': 'equal'},
    )

    login_user(member2.email, member2_pass)
    response = client.get(f'/groups/{group.id}')

    assert response.status_code == 200
    expenses = Expense.query.filter_by(group_id=group.id).all()
    assert len(expenses) == 2

    total = sum(float(e.amount) for e in expenses)
    assert total == 150.00

    data_response = client.get(f'/groups/{group.id}/data')
    data = json.loads(data_response.data)
    assert data['group']['total_spent'] == 150.00
