"""Add paid_amount to expense_splits for partial payment tracking

Revision ID: a3f7e1d2c890
Revises: d5e8c2b4f901
Create Date: 2026-05-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f7e1d2c890'
down_revision = 'd5e8c2b4f901'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('expense_splits', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'paid_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default='0',
        ))
    # Backfill: rows already marked is_paid=1 have been fully settled.
    op.execute(
        "UPDATE expense_splits SET paid_amount = share_amount WHERE is_paid = 1"
    )


def downgrade():
    with op.batch_alter_table('expense_splits', schema=None) as batch_op:
        batch_op.drop_column('paid_amount')
