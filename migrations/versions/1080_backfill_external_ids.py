"""Backfill external ID column

Revision ID: 1080
Revises: 1070
Create Date: 2017-12-05 15:00:00.00000

"""
from alembic import op
import json
import random
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '1080'
down_revision = '1070'

DIRECT_AWARD_AUDIT_TYPES = ('create_project', 'create_project_search', 'lock_project', 'downloaded_project')

# revision identifiers, used by Alembic.
revision = '1080'
down_revision = '1070'


def random_positive_external_id():
    return random.SystemRandom().randint(10 ** 14, (10 ** 15) - 1)


def upgrade():
    # Grab existing external IDs and populate the translation table
    project_id_internal_to_external = {}
    project_prefill_connection = op.get_bind()
    for internal_id, external_id in project_prefill_connection.execute(
            'SELECT id, external_id FROM direct_award_projects WHERE external_id IS NOT NULL'
    ):
        project_id_internal_to_external[internal_id] = external_id

    # Manually generate random IDs for all existing saved searches
    project_connection = op.get_bind()
    for row_id, *_ in project_connection.execute('SELECT id FROM direct_award_projects WHERE external_id IS NULL'):
        # Some logic to ensure all IDs generated are unique; keep track so we can update AuditEvents.
        random_id = random_positive_external_id()
        while random_id in project_id_internal_to_external.values():
            random_id = random_positive_external_id()
        project_id_internal_to_external[row_id] = random_id

        project_connection.execute(text('UPDATE direct_award_projects SET external_id = :external_id WHERE id = :id'),
                                   {'external_id': random_id, 'id': row_id})

    # Inject external IDs into existing Audit Events to allow them to be searched by the reference that we are likely
    # to be given e.g. by support enquiries.
    audit_connection = op.get_bind()
    for audit_id, audit_data, project_id in audit_connection.execute(
            text("SELECT id, data, (data->>'projectId')::int FROM audit_events WHERE type IN :audit_types"),
            {'audit_types': DIRECT_AWARD_AUDIT_TYPES}
    ):
        if project_id:
            # If for some hellish reason we are re-running this after external IDs already exist, our audit events
            # should keep the original external ID (ie not be overwritten).
            new_audit_data = json.dumps(
                    {'projectExternalId': project_id_internal_to_external[project_id], **audit_data}
            )
            audit_connection.execute(
                    text('UPDATE audit_events SET data = (:new_audit_data)::json WHERE id = :audit_id'),
                    {'new_audit_data': new_audit_data, 'audit_id': audit_id}
            )

    op.alter_column('direct_award_projects', 'external_id', existing_type=sa.BigInteger(), nullable=False)


def downgrade():
    op.alter_column('direct_award_projects', 'external_id', existing_type=sa.BigInteger(), nullable=True)

    # I don't think we ought to delete the external ID from the Audit Event on a downgrade... But if we do, here's
    # the code.
    """
    audit_connection = op.get_bind()
    for audit_id, audit_data, project_id in audit_connection.execute(
            text('SELECT id, data, object_id FROM audit_events WHERE type IN :audit_types'),
            {'audit_types': DIRECT_AWARD_AUDIT_TYPES}
    ):
        if 'projectExternalId' in audit_data:
            del audit_data['projectExternalId']

        new_audit_data = json.dumps(audit_data)
        audit_connection.execute(text('UPDATE audit_events SET data = (:new_audit_data)::json WHERE id = :audit_id'),
                                 {'new_audit_data': new_audit_data, 'audit_id': audit_id})
     """
