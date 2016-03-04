"""Remove brief status column

Revision ID: 590
Revises: 580
Create Date: 2016-03-03 14:56:59.218753

"""

# revision identifiers, used by Alembic.
revision = '590'
down_revision = '580'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('briefs', 'status')


def downgrade():
    op.add_column('briefs', sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.execute("""
        UPDATE briefs SET status = (CASE WHEN published_at is not NULL THEN 'live' ELSE 'draft' END)
    """)
    op.alter_column('briefs', sa.Column('status', sa.VARCHAR(), nullable=False))
