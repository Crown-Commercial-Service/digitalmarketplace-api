"""Add published_at to briefs

Revision ID: 560
Revises: 550
Create Date: 2016-02-01 10:27:03.370558

"""

# revision identifiers, used by Alembic.
revision = '560'
down_revision = '550'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('briefs', sa.Column('published_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_briefs_published_at'), 'briefs', ['published_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_briefs_published_at'), table_name='briefs')
    op.drop_column('briefs', 'published_at')
