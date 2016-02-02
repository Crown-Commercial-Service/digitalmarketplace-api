"""Rename framework gcloud to g-cloud

Revision ID: 490
Revises: 480
Create Date: 2016-01-29 16:08:51.484729

"""

# revision identifiers, used by Alembic.
revision = '490'
down_revision = '480'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
        UPDATE frameworks SET framework='g-cloud' WHERE framework='gcloud'
    """)


def downgrade():
    op.execute("""
        UPDATE frameworks SET framework='gcloud' WHERE framework='g-cloud'
    """)
