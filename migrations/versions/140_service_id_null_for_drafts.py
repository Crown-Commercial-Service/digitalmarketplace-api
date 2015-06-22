"""empty message

Revision ID: 140_service_id_null_for_drafts
Revises: 130_acknowledged_at_column
Create Date: 2015-06-22 10:42:37.274484

"""

# revision identifiers, used by Alembic.
revision = '140_service_id_null_for_drafts'
down_revision = '130_acknowledged_at_column'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('draft_services', 'service_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_index('ix_draft_services_service_id', table_name='draft_services')
    op.create_index(op.f('ix_draft_services_service_id'), 'draft_services', ['service_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_draft_services_service_id'), table_name='draft_services')
    op.create_index('ix_draft_services_service_id', 'draft_services', ['service_id'], unique=True)
    op.alter_column('draft_services', 'service_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
