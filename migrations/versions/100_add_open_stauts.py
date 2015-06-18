"""Add open status to framework table

Revision ID: 100_add_open_status
Revises: 90_add_gcloud_7
Create Date: 2015-06-18 08:43:33.427050

"""

# revision identifiers, used by Alembic.
revision = '100_add_open_status'
down_revision = '90_add_gcloud_7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("COMMIT") # See: http://stackoverflow.com/a/30910417/15720
    op.execute("ALTER TYPE framework_status_enum ADD VALUE 'open' AFTER 'pending';")


def downgrade():
    raise NotImplemented("Cannot remove framework value")
