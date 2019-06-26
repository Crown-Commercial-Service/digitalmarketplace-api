"""set suppliers active flag NOT NULLABLE

Ensure that all suppliers are either active or inactive.

Revision ID: 1340
Revises: 1330
Create Date: 2019-06-26 11:53:56.085586

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1340'
down_revision = '1330'


def upgrade():
    # We want this column to be NOT NULLABLE, so we need to set any NULL
    # values. NULLs are active suppliers (i.e. they have not been made
    # inactive).
    op.execute("UPDATE suppliers SET active = true WHERE active is NULL")
    op.alter_column('suppliers', 'active', nullable=False)


def downgrade():
    op.alter_column('suppliers', 'active', nullable=True)
