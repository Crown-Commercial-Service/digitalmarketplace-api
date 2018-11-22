"""Add CCS admin data controller role

Revision ID: 1270
Revises: 1260
Create Date: 2018-11-22 14:51:03.013362

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1270'
down_revision = '1260'


def upgrade():
    op.execute("COMMIT")  # See: http://stackoverflow.com/a/30910417/15720
    op.execute("ALTER TYPE user_roles_enum ADD VALUE IF NOT EXISTS 'admin-ccs-data-controller' AFTER 'admin-framework-manager';")


def downgrade():
    # Cannot remove user role value
    pass
