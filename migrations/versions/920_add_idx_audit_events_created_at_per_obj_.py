"""add_idx_audit_events_created_at_per_obj_partial

Revision ID: 920
Revises: 910
Create Date: 2017-06-19 11:17:00.565988

"""

# revision identifiers, used by Alembic.
revision = '920'
down_revision = '910'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_index(
        'idx_audit_events_created_at_per_obj_partial',
        'audit_events',
        ['object_type', 'object_id', 'created_at', 'id'],
        unique=False,
        postgresql_where=sa.text(u"acknowledged = false AND type = 'update_service'"),
    )


def downgrade():
    op.drop_index('idx_audit_events_created_at_per_obj_partial', table_name='audit_events')
