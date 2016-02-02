"""Add status to briefs

Revision ID: 550
Revises: 540
Create Date: 2016-01-28 16:51:32.608165

"""

# revision identifiers, used by Alembic.
revision = '550'
down_revision = '540'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('briefs', sa.Column('status', sa.String(), nullable=False))


def downgrade():
    op.drop_column('briefs', 'status')
