"""Add Brief.is_a_copy boolean, default False, nullable False

Revision ID: 890
Revises: 880
Create Date: 2017-06-01 11:24:53.346954

"""

# revision identifiers, used by Alembic.
revision = '900'
down_revision = '890'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('briefs', sa.Column('is_a_copy', sa.Boolean(), server_default=sa.text(u'false'), nullable=False))


def downgrade():
    op.drop_column('briefs', 'is_a_copy')
