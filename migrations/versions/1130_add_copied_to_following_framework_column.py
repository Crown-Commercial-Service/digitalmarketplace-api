"""add_copied_to_following_framework_column

Revision ID: 1130
Revises: 1120
Create Date: 2018-04-06 11:52:17.825501

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1130'
down_revision = '1120'


def upgrade():
    op.add_column('archived_services', sa.Column('copied_to_following_framework', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('draft_services', sa.Column('copied_to_following_framework', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('services', sa.Column('copied_to_following_framework', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade():
    op.drop_column('services', 'copied_to_following_framework')
    op.drop_column('draft_services', 'copied_to_following_framework')
    op.drop_column('archived_services', 'copied_to_following_framework')
