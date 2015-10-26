"""Migrate g-cloud-7 interested suppliers

Currently "registered interest" is stored in the audit events table.
We instead want to use the supplier_frameworks table to record this
information.

This migration extracts supplier IDs from the relevant audit events
and adds them to the supplier_frameworks table.

Revision ID: 350_migrate_interested_suppliers
Revises: 340
Create Date: 2015-10-05 19:10:42.467269

"""

# revision identifiers, used by Alembic.
revision = '350_migrate_interested_suppliers'
down_revision = '340'

from alembic import op


def upgrade():
    op.execute("""
        INSERT INTO supplier_frameworks
            (supplier_id, framework_id)
        SELECT DISTINCT users.supplier_id AS supplier_id, frameworks.id AS framework_id
            FROM users, audit_events, frameworks
                WHERE audit_events.user = users.email_address
                AND audit_events.type = 'register_framework_interest'
                AND frameworks.slug = 'g-cloud-7'
                AND (users.supplier_id, frameworks.id) NOT IN
                    (SELECT supplier_id, framework_id FROM supplier_frameworks);
    """)

def downgrade():
    op.execute("""
        DELETE FROM supplier_frameworks
            WHERE declaration IS NULL
            AND framework_id = 
                (SELECT id FROM frameworks 
                    WHERE frameworks.slug = 'g-cloud-7');
    """)
