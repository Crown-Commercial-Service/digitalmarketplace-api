"""change signer_details to agreement_details

Revision ID: 660
Revises: 650
Create Date: 2016-07-01 15:10:17.026710

"""

# revision identifiers, used by Alembic.
revision = '660'
down_revision = '650'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute('alter table supplier_framework rename signer_details to agreement_details')


def downgrade():
    op.execute('alter table supplier_framework rename agreement_details to signer_details')
