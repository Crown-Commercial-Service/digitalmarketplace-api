"""framework agreement on hold at

Revision ID: 750
Revises: 740
Create Date: 2016-09-26 11:09:26.852142

"""

# revision identifiers, used by Alembic.
revision = '750'
down_revision = '740'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('framework_agreements', sa.Column('signed_agreement_put_on_hold_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('framework_agreements', 'signed_agreement_put_on_hold_at')
