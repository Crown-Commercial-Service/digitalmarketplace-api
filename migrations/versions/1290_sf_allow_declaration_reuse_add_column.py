"""sf_allow_declaration_reuse_add_column

create supplier_frameworks.allow_declaration_reuse column as nullable in an initial, small
transaction. we will backfill it with defaults later to minimize table locking time.

Revision ID: 1290
Revises: 1280
Create Date: 2019-06-10 17:00:02.464675

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1290'
down_revision = '1280'


def upgrade():
    # create column as nullable in an initial, small transaction. we will backfill it with defaults later
    op.add_column('supplier_frameworks', sa.Column('allow_declaration_reuse', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('supplier_frameworks', 'allow_declaration_reuse')
