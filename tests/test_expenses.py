from models import Expense, ExpenseSplit
from tests.conftest import login


class TestDeleteExpense:
    def test_delete_removes_expense_and_splits(self, client, db, user, expense):
        login(client)
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/delete',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'deleted successfully' in resp.data
        assert Expense.query.get(expense.id) is None
        assert ExpenseSplit.query.filter_by(expense_id=expense.id).count() == 0

    def test_delete_nonexistent_expense_404(self, client, db, user, group):
        login(client)
        resp = client.post(f'/groups/{group.id}/expenses/9999/delete')
        assert resp.status_code == 404

    def test_delete_wrong_group_404(self, client, db, user, other_user, expense):
        login(client)
        g2_id = expense.group_id + 100
        resp = client.post(f'/groups/{g2_id}/expenses/{expense.id}/delete')
        assert resp.status_code == 404

    def test_delete_requires_login(self, client, expense):
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/delete',
        )
        assert resp.status_code == 302
        assert '/login' in resp.headers['Location']

    def test_delete_non_member_404(self, client, db, other_user, expense):
        login(client, email='bob@test.com')
        new_group_id = 9999
        resp = client.post(f'/groups/{new_group_id}/expenses/{expense.id}/delete')
        assert resp.status_code == 404

    def test_delete_by_non_payer_member(self, client, db, other_user, expense):
        login(client, email='bob@test.com')
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/delete',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'deleted successfully' in resp.data
        assert Expense.query.get(expense.id) is None


class TestEditExpense:
    def test_edit_updates_all_fields(self, client, db, user, expense):
        login(client)
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': 'Updated groceries',
                'amount': '200.00',
                'category': 'Food',
                'expense_date': '2026-06-15',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'updated successfully' in resp.data
        updated = db.session.get(Expense, expense.id)
        assert updated.description == 'Updated groceries'
        assert float(updated.amount) == 200.00
        assert updated.date.isoformat() == '2026-06-15'

    def test_edit_recalculates_equal_splits(self, client, db, user, other_user, expense):
        login(client)
        client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': 'Groceries',
                'amount': '200.00',
                'category': 'Food',
                'expense_date': '2026-05-01',
            },
        )
        splits = ExpenseSplit.query.filter_by(expense_id=expense.id).all()
        assert len(splits) == 2
        for s in splits:
            assert float(s.share_amount) == 100.00

    def test_edit_preserves_custom_splits(self, client, db, user, custom_expense):
        login(client)
        client.post(
            f'/groups/{custom_expense.group_id}/expenses/{custom_expense.id}/edit',
            data={
                'description': 'Fancy dinner',
                'amount': '120.00',
                'category': 'Entertainment',
                'expense_date': '2026-05-02',
            },
        )
        updated = db.session.get(Expense, custom_expense.id)
        assert updated.description == 'Fancy dinner'
        assert float(updated.amount) == 120.00
        assert updated.category == 'Entertainment'
        splits = {s.user_id: float(s.share_amount) for s in updated.splits}
        assert splits[user.id] == 60.00
        assert splits[custom_expense.payer.id] == 60.00

    def test_edit_missing_description(self, client, db, user, expense):
        login(client)
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': '',
                'amount': '50.00',
                'category': 'Food',
                'expense_date': '2026-05-01',
            },
            follow_redirects=True,
        )
        assert b'Description is required' in resp.data
        unchanged = db.session.get(Expense, expense.id)
        assert unchanged.description == 'Groceries'

    def test_edit_invalid_amount(self, client, db, user, expense):
        login(client)
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': 'Groceries',
                'amount': '-5',
                'category': 'Food',
                'expense_date': '2026-05-01',
            },
            follow_redirects=True,
        )
        assert b'Amount must be a positive number' in resp.data

    def test_edit_invalid_category(self, client, db, user, expense):
        login(client)
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': 'Groceries',
                'amount': '50.00',
                'category': 'InvalidCat',
                'expense_date': '2026-05-01',
            },
            follow_redirects=True,
        )
        assert b'valid category' in resp.data

    def test_edit_invalid_date(self, client, db, user, expense):
        login(client)
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': 'Groceries',
                'amount': '50.00',
                'category': 'Food',
                'expense_date': 'not-a-date',
            },
            follow_redirects=True,
        )
        assert b'Invalid date format' in resp.data

    def test_edit_missing_amount(self, client, db, user, expense):
        login(client)
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': 'Groceries',
                'amount': '',
                'category': 'Food',
                'expense_date': '2026-05-01',
            },
            follow_redirects=True,
        )
        assert b'Amount is required' in resp.data

    def test_edit_nonexistent_expense_404(self, client, db, user, group):
        login(client)
        resp = client.post(
            f'/groups/{group.id}/expenses/9999/edit',
            data={
                'description': 'x',
                'amount': '10',
                'category': 'Food',
                'expense_date': '2026-05-01',
            },
        )
        assert resp.status_code == 404

    def test_edit_requires_login(self, client, expense):
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={'description': 'x', 'amount': '10', 'category': 'Food'},
        )
        assert resp.status_code == 302
        assert '/login' in resp.headers['Location']

    def test_edit_changes_category(self, client, db, user, expense):
        login(client)
        client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': 'Groceries',
                'amount': '100.00',
                'category': 'Utilities',
                'expense_date': '2026-05-01',
            },
        )
        updated = db.session.get(Expense, expense.id)
        assert updated.category == 'Utilities'

    def test_edit_nonnumeric_amount(self, client, db, user, expense):
        login(client)
        resp = client.post(
            f'/groups/{expense.group_id}/expenses/{expense.id}/edit',
            data={
                'description': 'Groceries',
                'amount': 'abc',
                'category': 'Food',
                'expense_date': '2026-05-01',
            },
            follow_redirects=True,
        )
        assert b'valid number' in resp.data
