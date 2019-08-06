"""AuditEvent: add data['draftId'] partial index

Revision ID: 1390
Revises: 1380
Create Date: 2019-08-06 10:24:00.359631

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1390'
down_revision = '1380'


def upgrade():
    op.create_index(
        'idx_audit_events_data_draft_id',
        'audit_events',
        [sa.text("(data ->> 'draftId')")],
        unique=False,
        postgresql_where=sa.text("(data ->> 'draftId') IS NOT NULL"),
    )


def downgrade():
    op.drop_index('idx_audit_events_data_draft_id', table_name='audit_events')
