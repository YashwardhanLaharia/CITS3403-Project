"""Add user status for soft deletes

Revision ID: d5e8c2b4f901
Revises: ce5c9057a58a
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e8c2b4f901'
down_revision = 'ce5c9057a58a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=120), nullable=True)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=120), nullable=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('status')
