"""Add admin-ccs-sourcing role and rename admin-ccs to admin-ccs-category

Revision ID: 290_add_admin_ccs_sourcing_role
Revises: 280_switch_g7_framework_to_open
Create Date: 2015-09-07 11:10:00.000000

"""

# revision identifiers, used by Alembic.
revision = '290_add_admin_ccs_sourcing_role'
down_revision = '280_switch_g7_framework_to_open'

from alembic import op


def upgrade():
    op.execute("COMMIT")  # See: http://stackoverflow.com/a/30910417/15720
    op.execute("ALTER TYPE user_roles_enum ADD VALUE 'admin-ccs-category' AFTER 'admin-ccs';")
    op.execute("ALTER TYPE user_roles_enum ADD VALUE 'admin-ccs-sourcing' AFTER 'admin-ccs-category';")
    op.execute("UPDATE users SET role = 'admin-ccs-category' WHERE role = 'admin-ccs';")


def downgrade():
    op.execute("UPDATE users SET role = 'admin-ccs' WHERE role = 'admin-ccs-category';")
    # Can't remove values from enum so no way to roll that part back
