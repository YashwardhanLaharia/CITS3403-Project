import secrets
import string
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='active', server_default='active')
    deleted_at = db.Column(db.DateTime, nullable=True)

    memberships = db.relationship('Membership', back_populates='user', lazy='dynamic')
    created_groups = db.relationship('Group', back_populates='creator', lazy='dynamic')
    expenses_paid = db.relationship('Expense', back_populates='payer', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def display_name(self):
        base = f'{self.first_name} {self.last_name}'
        if self.status != 'active':
            return f'{base} (deleted)'
        return base

    @property
    def is_active(self):
        return self.status == 'active'

    def __repr__(self):
        return f'<User {self.email}>'


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='AUD')
    invite_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    creator = db.relationship('User', back_populates='created_groups')
    memberships = db.relationship('Membership', back_populates='group', lazy='dynamic')
    expenses = db.relationship('Expense', back_populates='group', lazy='dynamic')

    @staticmethod
    def generate_invite_code():
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not Group.query.filter_by(invite_code=code).first():
                return code

    def __repr__(self):
        return f'<Group {self.name}>'


class Membership(db.Model):
    __tablename__ = 'memberships'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', back_populates='memberships')
    group = db.relationship('Group', back_populates='memberships')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'group_id', name='unique_user_group'),
    )

    def __repr__(self):
        return f'<Membership user_id={self.user_id} group_id={self.group_id} role={self.role}>'


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    split_type = db.Column(db.String(20), nullable=False, server_default='equal')

    group = db.relationship('Group', back_populates='expenses')
    payer = db.relationship('User', foreign_keys=[paid_by], back_populates='expenses_paid')
    splits = db.relationship('ExpenseSplit', back_populates='expense', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Expense {self.description} ${self.amount}>'


class ExpenseSplit(db.Model):
    __tablename__ = 'expense_splits'

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    share_amount = db.Column(db.Numeric(10, 2), nullable=False)
    is_paid = db.Column(db.Boolean, default=False)

    expense = db.relationship('Expense', back_populates='splits')
    user = db.relationship('User')

    __table_args__ = (
        db.UniqueConstraint('expense_id', 'user_id', name='unique_expense_user_split'),
    )

    def __repr__(self):
        return f'<ExpenseSplit expense_id={self.expense_id} user_id={self.user_id} amount={self.share_amount}>'
