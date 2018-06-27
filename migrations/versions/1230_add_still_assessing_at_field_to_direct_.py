"""add still assessing at field to direct award project

Revision ID: 1230
Revises: 1220
Create Date: 2018-06-22 11:38:57.559198

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1230'
down_revision = '1220'


def upgrade():
    op.add_column('direct_award_projects', sa.Column('still_assessing_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('direct_award_projects', 'still_assessing_at')
