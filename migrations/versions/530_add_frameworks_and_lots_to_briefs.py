"""Add frameworks and lots to briefs

Revision ID: 530
Revises: 520
Create Date: 2016-01-26 13:30:31.602285

"""

# revision identifiers, used by Alembic.
revision = '530'
down_revision = '520'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('briefs', sa.Column('framework_id', sa.Integer(), nullable=False))
    op.add_column('briefs', sa.Column('lot_id', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'briefs', 'frameworks', ['framework_id'], ['id'])
    op.create_foreign_key(None, 'briefs', 'lots', ['lot_id'], ['id'])
    op.create_foreign_key('briefs_framework_id_fkey1', 'briefs', 'framework_lots', ['framework_id', 'lot_id'], ['framework_id', 'lot_id'])


def downgrade():
    op.drop_column('briefs', 'lot_id')
    op.drop_column('briefs', 'framework_id')
