"""add countersign and signer details

Revision ID: 650
Revises: 640
Create Date: 2016-06-16 13:18:43.766961

"""

# revision identifiers, used by Alembic.
revision = '650'
down_revision = '640'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('supplier_frameworks', sa.Column('countersigned_at', sa.DateTime(), nullable=True))
    op.add_column('supplier_frameworks', sa.Column('signer_details', postgresql.JSON(), nullable=True))


def downgrade():
    op.drop_column('supplier_frameworks', 'signer_details')
    op.drop_column('supplier_frameworks', 'countersigned_at')
