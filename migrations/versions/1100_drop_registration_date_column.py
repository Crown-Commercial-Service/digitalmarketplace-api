"""Drop registration date column

Revision ID: 1100
Revises: 1090
Create Date: 2018-03-05 13:36:36.395640

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '1100'
down_revision = '1090'


def upgrade():
    op.drop_column('suppliers', 'registration_date')


def downgrade():
    op.add_column('suppliers', sa.Column('registration_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
