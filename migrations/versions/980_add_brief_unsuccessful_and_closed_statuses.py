"""Add 2 new status columns; one for 'unsuccessful', one for 'cancelled'.

Revision ID: 980
Revises: 970
Create Date: 2017-08-25 11:38:57.947569

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '980'
down_revision = '970'


def upgrade():
    op.add_column('briefs', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
    op.add_column('briefs', sa.Column('unsuccessful_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_briefs_cancelled_at'), 'briefs', ['cancelled_at'], unique=False)
    op.create_index(op.f('ix_briefs_unsuccessful_at'), 'briefs', ['unsuccessful_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_briefs_unsuccessful_at'), table_name='briefs')
    op.drop_index(op.f('ix_briefs_cancelled_at'), table_name='briefs')
    op.drop_column('briefs', 'unsuccessful_at')
    op.drop_column('briefs', 'cancelled_at')
