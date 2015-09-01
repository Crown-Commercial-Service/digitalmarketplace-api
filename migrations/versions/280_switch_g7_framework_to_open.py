"""Add audit_events type, object and created_at indexes

Revision ID: 280_switch_g7_framework_to_open
Revises: 270_add_audit_events_indexes
Create Date: 2015-09-01 13:45:44.886576

"""

# revision identifiers, used by Alembic.
revision = '280_switch_g7_framework_to_open'
down_revision = '270_add_audit_events_indexes'

from alembic import op


def upgrade():
    op.execute("UPDATE frameworks SET status='open' WHERE name='G-Cloud 7'")


def downgrade():
    pass

