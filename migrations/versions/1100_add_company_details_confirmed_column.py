"""add company details confirmed column

Revision ID: 1100
Revises: 1090
Create Date: 2018-03-06 09:05:13.221057

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1100'
down_revision = '1090'


def upgrade():
    op.add_column('suppliers', sa.Column('company_details_confirmed', sa.Boolean(), nullable=False))


def downgrade():
    op.drop_column('suppliers', 'company_details_confirmed')

