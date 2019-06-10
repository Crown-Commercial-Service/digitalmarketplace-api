"""sf_allow_declaration_reuse_not_null

make supplier_frameworks.allow_declaration_reuse not-null in own transaction to minimize time table is locked

Revision ID: 1310
Revises: 1300
Create Date: 2019-06-10 17:20:24.762848

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1310'
down_revision = '1300'


def upgrade():
    # make column not-null in own transaction to minimize time table is locked
    op.alter_column(
        'supplier_frameworks',
        'allow_declaration_reuse',
        existing_type=sa.BOOLEAN(),
        nullable=False,
    )


def downgrade():
    op.alter_column(
        'supplier_frameworks',
        'allow_declaration_reuse',
        existing_type=sa.BOOLEAN(),
        nullable=True,
    )
