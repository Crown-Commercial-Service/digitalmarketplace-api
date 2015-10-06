"""Make G7 Pending

Revision ID: 300_make_g7_pending
Revises: 290_add_admin_ccs_sourcing_role
Create Date: 2015-10-06 12:45:44.886576

"""

# revision identifiers, used by Alembic.
revision = '300_make_g7_pending'
down_revision = '290_add_admin_ccs_sourcing_role'

from alembic import op


def upgrade():
    op.execute("UPDATE frameworks SET status='pending' WHERE name='G-Cloud 7'")


def downgrade():
    op.execute("UPDATE frameworks SET status='open' WHERE name='G-Cloud 7'")
