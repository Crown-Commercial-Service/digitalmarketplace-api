"""adding role to users

Revision ID: 3d5aabf7d291
Revises: 407e74de5553
Create Date: 2015-04-08 18:10:20.866273

"""

# revision identifiers, used by Alembic.
revision = '3d5aabf7d291'
down_revision = '407e74de5553'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('users', sa.Column('role', sa.String(), nullable=False))

    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role in ('supplier', 'admin', 'buyer')"
    )


def downgrade():
    op.drop_column('users', 'role')
