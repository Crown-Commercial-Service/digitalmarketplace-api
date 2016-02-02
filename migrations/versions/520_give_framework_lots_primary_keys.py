"""Give framework lots primary keys

Revision ID: 520
Revises: 510
Create Date: 2016-01-26 11:28:21.265740

"""

# revision identifiers, used by Alembic.
revision = '520'
down_revision = '510'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_primary_key("framework_lots_pkey", "framework_lots", ["framework_id", "lot_id"])


def downgrade():
    op.drop_constraint("framework_lots_pkey", "framework_lots")
