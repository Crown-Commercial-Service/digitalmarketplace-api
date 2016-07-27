"""brief withdrawn at

Revision ID: 680
Revises: 670
Create Date: 2016-07-25 10:22:21.258292

"""

# revision identifiers, used by Alembic.
revision = '680'
down_revision = '670'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('briefs', sa.Column('withdrawn_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_briefs_withdrawn_at'), 'briefs', ['withdrawn_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_briefs_withdrawn_at'), table_name='briefs')
    op.drop_column('briefs', 'withdrawn_at')
