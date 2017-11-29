"""Add admin-framework-manager role

Revision ID: 1060
Revises: 1050
Create Date: 2017-11-29 15:20:00.000000

"""

# revision identifiers, used by Alembic.
revision = '1060'
down_revision = '1050'

from alembic import op


def upgrade():
    op.execute("COMMIT")  # See: http://stackoverflow.com/a/30910417/15720
    op.execute("ALTER TYPE user_roles_enum ADD VALUE 'admin-framework-manager' AFTER 'admin-manager';")


def downgrade():
    # Cannot remove user role value
    pass
