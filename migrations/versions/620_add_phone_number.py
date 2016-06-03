"""Add phone number to users table

Revision ID: 620
Revises: 610
Create Date: 2016-05-25 10:45:58.171835

"""

# revision identifiers, used by Alembic.
revision = '620'
down_revision = '610'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'phone_number')
