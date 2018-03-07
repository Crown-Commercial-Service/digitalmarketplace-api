"""add company details confirmed column

Revision ID: 1110
Revises: 1100
Create Date: 2018-03-06 09:05:13.221057

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1110'
down_revision = '1100'


def upgrade():
    op.add_column('suppliers',
                  sa.Column(
                      'company_details_confirmed',
                      sa.Boolean(),
                      nullable=False,
                      default=False,
                      server_default=sa.sql.expression.literal(False)
                  )
                  )


def downgrade():
    op.drop_column('suppliers', 'company_details_confirmed')

