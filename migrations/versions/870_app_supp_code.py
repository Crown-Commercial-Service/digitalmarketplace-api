"""corrected supplier codes

Revision ID: b48fd3ae3d00
Revises: 870
Create Date: 2016-12-15 14:17:27.554023

"""

# revision identifiers, used by Alembic.
revision = '870'
down_revision = '860'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    update
        application a
    set
        supplier_code = (data->>'code')::bigint
    where
        supplier_code is null
        and (data->'code') is not null;
    """)


def downgrade():
    pass
