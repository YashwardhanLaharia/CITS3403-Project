from extensions import db as _db
from models import Expense, ExpenseSplit, Group, Membership


def test_user_cannot_access_other_users_group_dashboard(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-sec@example.com')
    group = group_factory(creator=admin)
    other, other_password = user_factory(email='other-sec@example.com')
    login_user(other.email, other_password)

    response = client.get(f'/groups/{group.id}')
    assert response.status_code == 404


def test_user_cannot_access_other_users_group_data_api(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-api-sec@example.com')
    group = group_factory(creator=admin)
    other, other_password = user_factory(email='other-api-sec@example.com')
    login_user(other.email, other_password)

    response = client.get(f'/groups/{group.id}/data')
    assert response.status_code == 404


def test_user_cannot_add_expense_to_other_users_group(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-exp-sec@example.com')
    group = group_factory(creator=admin)
    other, other_password = user_factory(email='other-exp-sec@example.com')
    login_user(other.email, other_password)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Unauthorized Expense',
            'amount': '100.00',
            'category': 'Food',
        },
    )
    assert response.status_code == 404


def test_logged_out_user_cannot_access_group_dashboard(client, user_factory, group_factory):
    admin, _ = user_factory(email='admin-logout@example.com')
    group = group_factory(creator=admin)

    response = client.get(f'/groups/{group.id}')
    assert response.status_code == 302


def test_logged_out_user_cannot_add_expenses(client, user_factory, group_factory):
    admin, _ = user_factory(email='admin-logout2@example.com')
    group = group_factory(creator=admin)

    response = client.post(
        f'/groups/{group.id}/expenses/add',
        data={
            'description': 'Test',
            'amount': '50.00',
            'category': 'Food',
        },
    )
    assert response.status_code == 302