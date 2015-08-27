"""Add audit_events type, object and created_at indexes

Revision ID: 270_add_audit_events_indexes
Revises: 260_add_admin_ccs_user_role
Create Date: 2015-08-26 11:18:44.886576

"""

# revision identifiers, used by Alembic.
revision = '270_add_audit_events_indexes'
down_revision = '260_add_admin_ccs_user_role'

from alembic import op


def upgrade():
    op.create_index(op.f('ix_audit_events_type'), 'audit_events', ['type'], unique=False)
    op.create_index('idx_audit_events_object', 'audit_events', ['object_type', 'object_id'], unique=False)
    op.create_index(op.f('ix_audit_events_created_at'), 'audit_events', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_audit_events_type'), table_name='audit_events')
    op.drop_index('idx_audit_events_object', table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_created_at'), table_name='audit_events')
