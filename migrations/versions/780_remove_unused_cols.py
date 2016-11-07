"""Remove agreement_returned_at, countersigned_at and agreement_details
   columns from supplier_framework table as they are no longer used

Revision ID: 780
Revises: 770
Create Date: 2016-11-07 10:14:00.000000

"""

# revision identifiers, used by Alembic.
revision = '780'
down_revision = '770'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('supplier_frameworks', 'agreement_returned_at')
    op.drop_column('supplier_frameworks', 'countersigned_at')
    op.drop_column('supplier_frameworks', 'agreement_details')


def downgrade():
    # Downgrade reinstates the columns but does not populate them with data.
    # These fields could be populated with data from the "current framework agreement" after being reinstated.
    # That would be better (or at least more easily) done by a script than by this migration if necessary.
    op.add_column('supplier_frameworks', sa.Column('agreement_returned_at', sa.DateTime(), nullable=True))
    op.add_column('supplier_frameworks', sa.Column('countersigned_at', sa.DateTime(), nullable=True))
    op.add_column('supplier_frameworks', sa.Column('agreement_details', sa.dialects.postgresql.JSON(), nullable=True))
