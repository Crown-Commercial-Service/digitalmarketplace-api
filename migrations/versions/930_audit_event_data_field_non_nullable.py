"""audit_event_data_field_non_nullable

Revision ID: 930
Revises: 920
Create Date: 2017-06-19 11:31:56.252791

"""

# revision identifiers, used by Alembic.
revision = '930'
down_revision = '920'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.alter_column(
        'audit_events',
        'data',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=False,
    )


def downgrade():
    op.alter_column(
        'audit_events',
        'data',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
    )
