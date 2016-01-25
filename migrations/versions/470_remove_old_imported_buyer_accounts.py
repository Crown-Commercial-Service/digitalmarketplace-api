"""Remove old imported buyer accounts

Revision ID: 470
Revises: 460
Create Date: 2016-01-22 16:20:29.793439

"""

# revision identifiers, used by Alembic.
revision = '470'
down_revision = '460'

from alembic import op


def upgrade():
    op.execute("""
        DELETE FROM users
        WHERE users.role = 'buyer';
    """)


def downgrade():
    pass  # :(
