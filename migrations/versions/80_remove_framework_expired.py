"""Remove framework expired column

Revision ID: 80_remove_framework_expired
Revises: 70_add_framework_status
Create Date: 2015-06-16 15:44:21.263411

"""

# revision identifiers, used by Alembic.
revision = '80_remove_framework_expired'
down_revision = '70_add_framework_status'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('frameworks', 'expired')


def downgrade():
    op.add_column('frameworks',
                  sa.Column('expired', sa.BOOLEAN(),
                            autoincrement=False, nullable=False, default=True))
    op.execute("UPDATE frameworks SET expired = TRUE WHERE status != 'live';")
    op.execute("UPDATE frameworks SET expired = FALSE WHERE status = 'live';")
    op.alter_column('frameworks', 'framework', server_default=None)
