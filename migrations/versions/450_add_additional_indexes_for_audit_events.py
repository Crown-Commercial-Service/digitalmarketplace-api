"""Add additional indexes for audit_events

Revision ID: 450
Revises: 440
Create Date: 2016-01-08 15:14:18.621169

"""

revision = '450'
down_revision = '440'

from alembic import op


def upgrade():
    op.create_index('idx_audit_events_object_and_type', 'audit_events',
                    ['object_type', 'object_id', 'type', 'created_at'], unique=False)
    op.create_index('idx_audit_events_type_acknowledged', 'audit_events',
                    ['type', 'acknowledged'], unique=False)
    op.drop_index('idx_audit_events_object', table_name='audit_events')


def downgrade():
    op.create_index('idx_audit_events_object', 'audit_events',
                    ['object_type', 'object_id'], unique=False)
    op.drop_index('idx_audit_events_type_acknowledged', table_name='audit_events')
    op.drop_index('idx_audit_events_object_and_type', table_name='audit_events')
