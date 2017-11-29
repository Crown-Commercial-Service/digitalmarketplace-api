"""Add admin-manager role

Revision ID: 1050
Revises: 1040
Create Date: 2017-11-21 11:20:00.000000

"""

# revision identifiers, used by Alembic.
revision = '1050'
down_revision = '1040'

from alembic import op


def upgrade():
    op.execute("COMMIT")  # See: http://stackoverflow.com/a/30910417/15720
    op.execute("ALTER TYPE user_roles_enum ADD VALUE IF NOT EXISTS 'admin-manager' AFTER 'admin-ccs-sourcing';")


def downgrade():
    # Cannot remove user role value
    pass
