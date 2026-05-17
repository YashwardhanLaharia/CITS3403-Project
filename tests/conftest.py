import pytest
from datetime import date
from app import create_app
from extensions import db as _db
from models import User, Group, Membership, Expense, ExpenseSplit


@pytest.fixture()
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user(db):
    u = User(email='alice@test.com', first_name='Alice', last_name='Smith')
    u.set_password('password123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def other_user(db):
    u = User(email='bob@test.com', first_name='Bob', last_name='Jones')
    u.set_password('password123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def group(db, user):
    g = Group(name='Test Group', currency='AUD', invite_code='TESTCODE', created_by=user.id)
    db.session.add(g)
    db.session.flush()
    m = Membership(user_id=user.id, group_id=g.id, role='admin')
    db.session.add(m)
    db.session.commit()
    return g


@pytest.fixture()
def group_with_both(db, group, other_user):
    m = Membership(user_id=other_user.id, group_id=group.id, role='member')
    db.session.add(m)
    db.session.commit()
    return group


@pytest.fixture()
def expense(db, group_with_both, user, other_user):
    e = Expense(
        group_id=group_with_both.id,
        paid_by=user.id,
        description='Groceries',
        amount=100.00,
        category='Food',
        date=date(2026, 5, 1),
        split_type='equal',
    )
    db.session.add(e)
    db.session.flush()
    for uid in [user.id, other_user.id]:
        s = ExpenseSplit(expense_id=e.id, user_id=uid, share_amount=50.00)
        db.session.add(s)
    db.session.commit()
    return e


@pytest.fixture()
def custom_expense(db, group_with_both, user, other_user):
    e = Expense(
        group_id=group_with_both.id,
        paid_by=user.id,
        description='Custom dinner',
        amount=90.00,
        category='Food',
        date=date(2026, 5, 2),
        split_type='custom',
    )
    db.session.add(e)
    db.session.flush()
    db.session.add(ExpenseSplit(expense_id=e.id, user_id=user.id, share_amount=60.00))
    db.session.add(ExpenseSplit(expense_id=e.id, user_id=other_user.id, share_amount=30.00))
    db.session.commit()
    return e


def login(client, email='alice@test.com', password='password123'):
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)
