"""Add additional indexes for audit_events

Revision ID: 460
Revises: 450
Create Date: 2016-01-13 16:45:18.621169

"""

revision = '460'
down_revision = '450'

from alembic import op


def upgrade():
    # G-Cloud 4
    op.execute("""
        INSERT INTO audit_events
            ("type", "created_at", "user", "data", "object_type", "object_id", "acknowledged")
        VALUES 
            ('framework_update', '2015-01-31T14:00:00', 'migration', '{"update": {"status": "expired"}}', 'Framework', 2, FALSE)
    """)


def downgrade():
    op.execute("""
        DELETE FROM audit_events WHERE
            "type"='framework_update' AND "created_at"='2015-01-31T14:00:00' AND "object_type"='Framework' AND "object_id"=2
    """)
