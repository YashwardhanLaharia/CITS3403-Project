import sys
from datetime import datetime, date
from random import choice, uniform

sys.path.insert(0, '.')

from app import create_app
from extensions import db
from models import User, Group, Membership, Expense, ExpenseSplit


def seed():
    app = create_app('development')
    with app.app_context():
        db.drop_all()
        db.create_all()

        user1 = User(
            email='alice@example.com',
            first_name='Alice',
            last_name='Anderson'
        )
        user1.set_password('alice_password')

        user2 = User(
            email='bob@example.com',
            first_name='Bob',
            last_name='Baker'
        )
        user2.set_password('bob_password')

        user3 = User(
            email='charlie@example.com',
            first_name='Charlie',
            last_name='Cox'
        )
        user3.set_password('charlie_password')
        db.session.add_all([user1, user2, user3])
        db.session.commit()

        group = Group(
            name='Summer Roadtrip',
            currency='AUD',
            invite_code='SRD24AUD',
            created_by=user1.id,
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 10)
        )
        db.session.add(group)
        db.session.commit()

        membership1 = Membership(
            user_id=user1.id,
            group_id=group.id,
            role='admin'
        )
        membership2 = Membership(
            user_id=user2.id,
            group_id=group.id,
            role='member'
        )
        membership3 = Membership(
            user_id=user3.id,
            group_id=group.id,
            role='member'
        )
        db.session.add_all([membership1, membership2, membership3])

        expenses = [
            Expense(
                group_id=group.id,
                paid_by=user1.id,
                description='Petrol',
                amount=60.00,
                category='Transport',
                date=date(2024, 7, 1),
                split_type='equal'
            ),
            Expense(
                group_id=group.id,
                paid_by=user2.id,
                description='Groceries',
                amount=45.50,
                category='Food',
                date=date(2024, 7, 2),
                split_type='equal'
            ),
            Expense(
                group_id=group.id,
                paid_by=user3.id,
                description='Hotel',
                amount=150.00,
                category='Accommodation',
                date=date(2024, 7, 3),
                split_type='equal'
            ),
            Expense(
                group_id=group.id,
                paid_by=user1.id,
                description='Dinner',
                amount=85.00,
                category='Food',
                date=date(2024, 7, 4),
                split_type='equal'
            ),
            Expense(
                group_id=group.id,
                paid_by=user2.id,
                description='Museum tickets',
                amount=30.00,
                category='Entertainment',
                date=date(2024, 7, 5),
                split_type='equal'
            ),
        ]
        db.session.add_all(expenses)
        db.session.commit()

        member_ids = [user1.id, user2.id, user3.id]
        
        for expense in expenses:
            share = float(expense.amount) / 3
            for member_id in member_ids:
                is_paid = (member_id == expense.paid_by)
                split = ExpenseSplit(
                    expense_id=expense.id,
                    user_id=member_id,
                    share_amount=share,
                    is_paid=is_paid
                )
                db.session.add(split)
        db.session.commit()

        # Second group with custom split example (trip dinner)
        group2 = Group(
            name='Dinner Party',
            currency='AUD',
            invite_code='DINNER22',
            created_by=user2.id,
            start_date=date(2024, 7, 15),
            end_date=date(2024, 7, 15)
        )
        db.session.add(group2)
        db.session.commit()

        # Add members to group2
        mem2_memberships = [
            Membership(user_id=user1.id, group_id=group2.id, role='member'),
            Membership(user_id=user2.id, group_id=group2.id, role='admin'),
            Membership(user_id=user3.id, group_id=group2.id, role='member'),
        ]
        db.session.add_all(mem2_memberships)
        db.session.commit()

        # Expense with custom split: all ate, user2 paid full amount
        custom_expense = Expense(
            group_id=group2.id,
            paid_by=user2.id,
            description='Restaurant Bill',
            amount=75.00,
            category='Food',
            date=date(2024, 7, 15),
            split_type='custom'
        )
        db.session.add(custom_expense)
        db.session.commit()

        # Custom splits - user1: $10, user2 (payer): $25, user3: $40
        custom_splits = [
            ExpenseSplit(expense_id=custom_expense.id, user_id=user1.id, share_amount=10.00, is_paid=False),
            ExpenseSplit(expense_id=custom_expense.id, user_id=user2.id, share_amount=25.00, is_paid=True),
            ExpenseSplit(expense_id=custom_expense.id, user_id=user3.id, share_amount=40.00, is_paid=False),
        ]
        db.session.add_all(custom_splits)
        db.session.commit()

        print('Seeded: 3 users, 2 groups, 6 memberships, 6 expenses')
        print(f'Group 1 invite code: {group.invite_code}')
        print(f'Group 2 invite code: {group2.invite_code}')


if __name__ == '__main__':
    seed()
