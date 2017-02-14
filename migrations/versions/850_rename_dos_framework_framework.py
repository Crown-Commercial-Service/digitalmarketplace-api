"""rename dos framework.framework

Revision ID: 850
Revises: 840
Create Date: 2017-02-03 02:06:40.438894

"""

# revision identifiers, used by Alembic.
revision = '850'
down_revision = '840'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
        UPDATE frameworks SET framework = 'digital-outcomes-and-specialists'
        WHERE framework = 'dos'
    """)


def downgrade():
    op.execute("""
        UPDATE frameworks SET framework = 'dos'
        WHERE framework = 'digital-outcomes-and-specialists'
    """)

