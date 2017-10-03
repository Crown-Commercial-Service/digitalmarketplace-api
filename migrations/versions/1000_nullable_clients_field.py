"""Nullable clients field

Revision ID: 1000
Revises: 990
Create Date: 2017-10-04 14:37:07.079122

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '1000'
down_revision = '990'


def upgrade():
    op.alter_column('suppliers', 'clients',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               nullable=True)


def downgrade():
    op.alter_column('suppliers', 'clients',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               nullable=False)

