import re
from datetime import datetime, date
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user, logout_user
from sqlalchemy import func
from extensions import db, login_manager
from models import User, Group, Membership, Expense, ExpenseSplit

main_bp = Blueprint('main', __name__)


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user is None:
        login_manager.unauthorized()
    return user


@main_bp.route('/')
@login_required
def index():
    memberships = Membership.query.filter_by(user_id=current_user.id).all()
    group_ids = [m.group_id for m in memberships]
    groups_by_id = {m.group_id: m.group for m in memberships}

    if not group_ids:
        return render_template('index.html', first_name=current_user.first_name, groups=[], net_balance=0.0)

    member_counts = dict(
        db.session.query(Membership.group_id, func.count(Membership.id))
        .filter(Membership.group_id.in_(group_ids))
        .group_by(Membership.group_id)
        .all()
    )

    spent_by_group = dict(
        db.session.query(Expense.group_id, func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.group_id.in_(group_ids))
        .group_by(Expense.group_id)
        .all()
    )

    paid_by_user = dict(
        db.session.query(Expense.group_id, func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.group_id.in_(group_ids), Expense.paid_by == current_user.id)
        .group_by(Expense.group_id)
        .all()
    )

    fair_shares = dict(
        db.session.query(Expense.group_id, func.coalesce(func.sum(ExpenseSplit.share_amount), 0))
        .join(ExpenseSplit, ExpenseSplit.expense_id == Expense.id)
        .filter(Expense.group_id.in_(group_ids), ExpenseSplit.user_id == current_user.id)
        .group_by(Expense.group_id)
        .all()
    )

    groups = []
    net_balance = 0.0

    for gid in group_ids:
        group = groups_by_id[gid]
        user_balance = float(paid_by_user.get(gid, 0)) - float(fair_shares.get(gid, 0))
        net_balance += user_balance

        groups.append({
            'id': group.id,
            'name': group.name,
            'currency': group.currency,
            'member_count': member_counts.get(gid, 0),
            'total_spent': float(spent_by_group.get(gid, 0)),
            'user_balance': user_balance,
        })

    return render_template(
        'index.html',
        first_name=current_user.first_name,
        groups=groups,
        net_balance=net_balance,
    )


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        errors = []

        if not email:
            errors.append('Email is required.')
        if not password:
            errors.append('Password is required.')

        if not errors:
            user = User.query.filter_by(email=email).first()
            if user and user.status == 'active' and user.check_password(password):
                from flask_login import login_user
                login_user(user, remember=bool(remember))
                next_page = request.args.get('next')
                flash(f'Welcome back, {user.first_name}!', 'success')
                return redirect(next_page or url_for('main.index'))
            else:
                errors.append('Invalid email or password.')

        for error in errors:
            flash(error, 'error')

    return render_template('login.html')


@main_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []

        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        if not email:
            errors.append('Email is required.')
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors.append('Please enter a valid email address.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        if email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                errors.append('An account with this email already exists.')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('signup.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   email=email)

        user = User(email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('main.login'))

    return render_template('signup.html')


@main_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    from flask_login import logout_user
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))


def _compute_group_data(members_by_id, expenses):
    """Compute per-member balances, category distribution, and settlement transfers.

    Returns (members, categories, transfers, total_spent).
    members dicts have keys: id, name, initials, paid, balance.
    categories dicts have keys: name, amount, pct.
    transfers dicts have keys: from_name, to_name, amount.
    """
    paid_totals = {uid: 0.0 for uid in members_by_id}
    share_totals = {uid: 0.0 for uid in members_by_id}
    category_totals = {}
    total_spent = 0.0

    for expense in expenses:
        amount = float(expense.amount)
        total_spent += amount
        paid_totals[expense.paid_by] = paid_totals.get(expense.paid_by, 0.0) + amount
        cat = expense.category or 'Other'
        category_totals[cat] = category_totals.get(cat, 0.0) + amount
        for split in expense.splits:
            share_totals[split.user_id] = share_totals.get(split.user_id, 0.0) + float(split.share_amount)

    members = [
        {
            'id': uid,
            'name': user.display_name,
            'initials': f'{user.first_name[0]}{user.last_name[0]}'.upper(),
            'paid': paid_totals.get(uid, 0.0),
            'balance': paid_totals.get(uid, 0.0) - share_totals.get(uid, 0.0),
        }
        for uid, user in members_by_id.items()
    ]

    categories = [
        {'name': cat, 'amount': amount, 'pct': round(amount / total_spent * 100, 1) if total_spent else 0}
        for cat, amount in sorted(category_totals.items(), key=lambda x: -x[1])
    ]

    # Greedy settlement: repeatedly match largest debtor with largest creditor
    raw_balances = {uid: paid_totals.get(uid, 0.0) - share_totals.get(uid, 0.0)
                    for uid in members_by_id}
    creditors = [[uid, bal] for uid, bal in sorted(raw_balances.items(), key=lambda x: -x[1]) if bal > 0.005]
    debtors = [[uid, -bal] for uid, bal in sorted(raw_balances.items(), key=lambda x: x[1]) if bal < -0.005]

    transfers = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt = debtors[i]
        creditor_id, credit = creditors[j]
        amount = min(debt, credit)
        transfers.append({
            'from_name': members_by_id[debtor_id].display_name,
            'to_name': members_by_id[creditor_id].display_name,
            'amount': round(amount, 2),
        })
        debtors[i][1] -= amount
        creditors[j][1] -= amount
        if debtors[i][1] < 0.005:
            i += 1
        if creditors[j][1] < 0.005:
            j += 1

    return members, categories, transfers, total_spent


@main_bp.route('/groups/<int:group_id>')
@login_required
def group_dashboard(group_id):
    membership = Membership.query.filter_by(
        group_id=group_id, user_id=current_user.id
    ).first_or_404()

    group = membership.group
    members_by_id = {m.user_id: m.user for m in Membership.query.filter_by(group_id=group_id).all()}
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.date.desc()).all()

    members, categories, transfers, total_spent = _compute_group_data(members_by_id, expenses)

    return render_template(
        'dashboard.html',
        group=group,
        members=members,
        expenses=expenses,
        categories=categories,
        transfers=transfers,
        total_spent=total_spent,
        expense_categories=EXPENSE_CATEGORIES,
    )


@main_bp.route('/groups/<int:group_id>/data')
@login_required
def group_data(group_id):
    Membership.query.filter_by(
        group_id=group_id, user_id=current_user.id
    ).first_or_404()

    group = Group.query.get_or_404(group_id)
    members_by_id = {m.user_id: m.user for m in Membership.query.filter_by(group_id=group_id).all()}
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.date.desc()).all()

    members, categories, transfers, total_spent = _compute_group_data(members_by_id, expenses)

    return jsonify({
        'group': {
            'id': group.id,
            'name': group.name,
            'currency': group.currency,
            'invite_code': group.invite_code,
            'total_spent': total_spent,
        },
        'members': [
            {
                'id': m['id'],
                'name': m['name'],
                'initials': m['initials'],
                'amount_paid': m['paid'],
                'balance': m['balance'],
            }
            for m in members
        ],
        'expenses': [
            {
                'id': e.id,
                'description': e.description,
                'amount': float(e.amount),
                'category': e.category,
                'date': e.date.strftime('%Y-%m-%d'),
                'paid_by': e.payer.display_name,
            }
            for e in expenses
        ],
        'categories': [
            {
                'name': c['name'],
                'amount': c['amount'],
                'percentage': c['pct'],
            }
            for c in categories
        ],
        'transfers': [
            {
                'from': t['from_name'],
                'to': t['to_name'],
                'amount': t['amount'],
            }
            for t in transfers
        ],
    })


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')

        errors = []

        if not current_password:
            errors.append('Current password is required to save changes.')
        elif not current_user.check_password(current_password):
            errors.append('Current password is incorrect.')

        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')

        if new_password and len(new_password) < 8:
            errors.append('New password must be at least 8 characters.')

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            current_user.first_name = first_name
            current_user.last_name = last_name
            if new_password:
                current_user.set_password(new_password)
                db.session.commit()
                logout_user()
                flash('Profile updated. Please log in with your new password.', 'success')
                return redirect(url_for('main.login'))
            db.session.commit()
            flash('Profile updated successfully.', 'success')

        return render_template('profile.html',
                               first_name=first_name or current_user.first_name,
                               last_name=last_name or current_user.last_name,
                               email=current_user.email,
                               created_at=current_user.created_at)

    return render_template('profile.html',
                           first_name=current_user.first_name,
                           last_name=current_user.last_name,
                           email=current_user.email,
                           created_at=current_user.created_at)


@main_bp.route('/profile/delete', methods=['POST'])
@login_required
def delete_account():
    delete_password = request.form.get('delete_password', '')
    if not delete_password:
        flash('Current password is required to delete your account.', 'error')
        return redirect(url_for('main.profile'))

    if not current_user.check_password(delete_password):
        flash('The password you entered is incorrect.', 'error')
        return redirect(url_for('main.profile'))

    current_user.status = 'deleted'
    current_user.deleted_at = datetime.utcnow()
    current_user.email = None
    db.session.commit()
    logout_user()
    flash('Your account was deleted. The data you contributed remains in shared groups.', 'info')
    return redirect(url_for('main.login'))


@main_bp.route('/groups/join', methods=['POST'])
@login_required
def join_group():
    invite_code = request.form.get('invite_code', '').strip().upper()

    group = Group.query.filter_by(invite_code=invite_code).first()
    if not group:
        flash('Invalid invite code. Please check and try again.', 'error')
        return redirect(url_for('main.index'))

    existing = Membership.query.filter_by(
        user_id=current_user.id, group_id=group.id
    ).first()
    if existing:
        flash('You are already a member of this group.', 'error')
        return redirect(url_for('main.index'))

    membership = Membership(user_id=current_user.id, group_id=group.id, role='member')
    db.session.add(membership)
    db.session.commit()

    flash(f'You have joined "{group.name}" successfully!', 'success')
    return redirect(url_for('main.index'))


@main_bp.route('/groups/create', methods=['POST'])
@login_required
def create_group():
    name = request.form.get('group_name', '').strip()
    currency = request.form.get('currency', '').strip()

    if not name:
        flash('Group name is required.', 'error')
        return redirect(url_for('main.index'))

    try:
        group = Group(
            name=name,
            currency=currency,
            invite_code=Group.generate_invite_code(),
            created_by=current_user.id,
        )
        db.session.add(group)
        db.session.flush()

        membership = Membership(
            user_id=current_user.id,
            group_id=group.id,
            role='admin',
        )
        db.session.add(membership)
        db.session.commit()

        flash(f'Group "{name}" created successfully!', 'success')
    except Exception:
        db.session.rollback()
        flash('Failed to create group. Please try again.', 'error')

    return redirect(url_for('main.index'))


EXPENSE_CATEGORIES = ['Food', 'Transport', 'Accommodation', 'Entertainment', 'Utilities', 'Other']


@main_bp.route('/groups/<int:group_id>/expenses/add', methods=['POST'])
@login_required
def add_expense(group_id):
    membership = Membership.query.filter_by(
        group_id=group_id, user_id=current_user.id
    ).first_or_404()

    description = request.form.get('description', '').strip()
    amount_str = request.form.get('amount', '').strip()
    category = request.form.get('category', '').strip()
    date_str = request.form.get('expense_date', '').strip()
    split_type = request.form.get('split_type', 'equal')

    errors = []
    if not description:
        errors.append('Description is required.')

    amount = None
    if not amount_str:
        errors.append('Amount is required.')
    else:
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors.append('Amount must be a positive number.')
        except ValueError:
            errors.append('Amount must be a valid number.')

    if category not in EXPENSE_CATEGORIES:
        errors.append('Please select a valid category.')

    if split_type not in ('equal', 'custom'):
        split_type = 'equal'

    expense_date = date.today()
    if date_str:
        try:
            expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append('Invalid date format.')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    members = Membership.query.filter_by(group_id=group_id).all()

    split_amounts = {}
    if split_type == 'custom' and amount is not None:
        total_split = 0.0
        for m in members:
            raw = request.form.get(f'split_amount_{m.user_id}', '0')
            try:
                share = round(float(raw), 2)
            except ValueError:
                errors.append('All split amounts must be valid numbers.')
                break
            if share < 0:
                errors.append('Split amounts cannot be negative.')
                break
            split_amounts[m.user_id] = share
            total_split += share
        if not errors and abs(total_split - amount) > 0.01:
            errors.append('Split amounts must add up to the total expense amount.')

    if errors:
        if is_ajax:
            return jsonify({'success': False, 'errors': errors}), 400
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('main.group_dashboard', group_id=group_id))

    expense = Expense(
        group_id=group_id,
        paid_by=current_user.id,
        description=description,
        amount=amount,
        category=category,
        date=expense_date,
        split_type=split_type,
    )
    db.session.add(expense)
    db.session.flush()

    if split_type == 'custom':
        for m in members:
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=m.user_id,
                share_amount=split_amounts[m.user_id],
            )
            db.session.add(split)
    else:
        share = round(amount / len(members), 2)
        for m in members:
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=m.user_id,
                share_amount=share,
            )
            db.session.add(split)

    db.session.commit()

    if is_ajax:
        return jsonify({'success': True})
    flash(f'Expense "{description}" added successfully!', 'success')
    return redirect(url_for('main.group_dashboard', group_id=group_id))


@main_bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
