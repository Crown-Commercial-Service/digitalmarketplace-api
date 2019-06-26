"""add suppliers active flag

Adds a new column to the suppliers table, 'active', that indicates whether a
supplier is currently valid.

Revision ID: 1330
Revises: 1320
Create Date: 2019-06-26 11:14:56.085586

"""
from alembic import context, op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1330'
down_revision = '1320'


def upgrade():
    # We want this column to be DEFAULT true, but creating a column
    # with defaults is a slow operation, so we split it up a bit.
    op.add_column('suppliers', sa.Column('active', sa.Boolean(), nullable=True))
    op.alter_column('suppliers', 'active', server_default=sa.text('true'))


def downgrade():
    op.drop_column('suppliers', 'active')
