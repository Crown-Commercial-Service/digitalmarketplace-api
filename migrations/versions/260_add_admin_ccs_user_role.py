"""Add admin-ccs user role

Revision ID: 260_add_admin_ccs_user_role
Revises: 250_enum_user_role
Create Date: 2015-08-20 10:12:23.403685

"""

# revision identifiers, used by Alembic.
revision = '260_add_admin_ccs_user_role'
down_revision = '250_enum_user_role'

from alembic import op


def upgrade():
    op.execute("COMMIT")  # See: http://stackoverflow.com/a/30910417/15720
    op.execute("ALTER TYPE user_roles_enum ADD VALUE 'admin-ccs' AFTER 'admin';")


def downgrade():
    raise NotImplemented("Cannot remove user role value")
