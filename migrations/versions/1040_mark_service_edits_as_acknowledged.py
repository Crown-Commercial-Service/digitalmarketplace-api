"""Mark all audit events of type "update_service" up to 19th October 2017 as acknowledged

Revision ID: 1040
Revises: 1030
Create Date: 2017-10-13 13:25:01.000000

"""

revision = '1040'
down_revision = '1030'

from alembic import op


def upgrade():
    op.execute("""
        UPDATE audit_events
           SET acknowledged = TRUE, acknowledged_by = 'pre-supplier-editing-migration-1040', acknowledged_at = NOW()
         WHERE type = 'update_service'
           AND acknowledged is FALSE
           AND created_at < '2017-10-19 00:00:00'
    """)


def downgrade():
    op.execute("""
        UPDATE audit_events
           SET acknowledged = FALSE, acknowledged_by = NULL, acknowledged_at = NULL
         WHERE acknowledged_by = 'pre-supplier-editing-migration-1040'
    """)
