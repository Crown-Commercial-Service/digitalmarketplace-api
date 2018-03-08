"""Adds user_research_opted_in column to user table

Revision ID: 1110
Revises: 1100
Create Date: 2018-02-28 13:37:21.460040

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1110'
down_revision = '1100'


def upgrade():
    op.add_column('users', sa.Column('user_research_opted_in', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    op.drop_column('users', 'user_research_opted_in')
