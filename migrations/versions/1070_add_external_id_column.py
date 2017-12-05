"""Add external ID column

Revision ID: 1070
Revises: 1060
Create Date: 2017-11-23 16:46:00.569239

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1070'
down_revision = '1060'


def upgrade():
    op.add_column('direct_award_projects', sa.Column('external_id', sa.BigInteger()))
    op.create_index(op.f('ix_direct_award_projects_external_id'), 'direct_award_projects', ['external_id'], unique=True)
    op.create_unique_constraint('uq_direct_award_projects_external_id', 'direct_award_projects', ['external_id'])


def downgrade():
    op.drop_index(op.f('ix_direct_award_projects_external_id'), table_name='direct_award_projects')
    op.drop_column('direct_award_projects', 'external_id')
