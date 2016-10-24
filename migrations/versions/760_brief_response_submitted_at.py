"""brief response submitted at

Revision ID: 760
Revises: 750
Create Date: 2016-10-24 14:16:29.951023

"""

# revision identifiers, used by Alembic.
revision = '760'
down_revision = '750'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('brief_responses', sa.Column('submitted_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('brief_responses', 'submitted_at')
