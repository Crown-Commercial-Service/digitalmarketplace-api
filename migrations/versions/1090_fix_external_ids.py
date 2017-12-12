"""Fix external IDs that were populated into 'create_project' audit events incorrectly

Revision ID: 1090
Revises: 1080
Create Date: 2017-12-12 09:10:00.00000

"""
from alembic import op
import json
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '1090'
down_revision = '1080'


def upgrade():
    # Grab existing external IDs and populate the translation table
    project_id_internal_to_external = {}
    project_prefill_connection = op.get_bind()
    for internal_id, external_id in project_prefill_connection.execute('SELECT id, external_id FROM direct_award_projects'):
        project_id_internal_to_external[internal_id] = external_id

    # For audit events that have stored an internal project ID (represented by IDs less than 1 million), update the data
    # using the translation table above to convert it to its external ID.
    audit_connection = op.get_bind()
    for audit_id, audit_data, project_id in audit_connection.execute(
            "SELECT id, data, object_id "
            "FROM audit_events "
            "WHERE type='create_project' AND (data->>'projectExternalId')::bigint < 1000000"
    ):
        new_audit_data = json.dumps(
                {**audit_data, 'projectExternalId': project_id_internal_to_external[project_id]}
        )
        audit_connection.execute(
                text('UPDATE audit_events '
                     'SET data = (:new_audit_data)::json '
                     'WHERE id = :audit_id'),
                {'new_audit_data': new_audit_data, 'audit_id': audit_id}
        )


def downgrade():
    # There is no appropriate downgrade path for this partial data migration.
    pass
