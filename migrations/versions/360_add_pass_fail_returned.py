""" Add columns to supplier_frameworks to indicate
    Pass/Fail and whether a Framework Agreement has
    been returned.

Revision ID: 360_add_pass_fail_returned
Revises: 350_migrate_interested_suppliers
Create Date: 2015-10-23 16:25:02.068155

"""

# revision identifiers, used by Alembic.
revision = '360_add_pass_fail_returned'
down_revision = '350_migrate_interested_suppliers'

from alembic import op
import sqlalchemy as sa


def upgrade():

    op.add_column('supplier_frameworks', sa.Column('agreement_returned', sa.Boolean(), nullable=True))
    op.add_column('supplier_frameworks', sa.Column('on_framework', sa.Boolean(), nullable=True))


def downgrade():

    op.drop_column('supplier_frameworks', 'on_framework')
    op.drop_column('supplier_frameworks', 'agreement_returned')
