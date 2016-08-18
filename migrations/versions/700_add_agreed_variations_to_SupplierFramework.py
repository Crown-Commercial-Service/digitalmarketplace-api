"""add agreed_variations to SupplierFramework

Revision ID: 700
Revises: 690
Create Date: 2016-08-12 15:52:48.366958

"""

# revision identifiers, used by Alembic.
revision = '700'
down_revision = '690'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('supplier_frameworks', sa.Column('agreed_variations', postgresql.JSON(), nullable=True))


def downgrade():
    op.drop_column('supplier_frameworks', 'agreed_variations')
