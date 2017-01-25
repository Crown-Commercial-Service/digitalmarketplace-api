"""empty message

Revision ID: 339de994d726
Revises: 910
Create Date: 2016-08-09 09:59:32.375205

"""

# revision identifiers, used by Alembic.
revision = '920'
down_revision = '910'

from alembic import op
import sqlalchemy as sa


def upgrade():
    from app import models
    op.bulk_insert(models.Framework.__table__, [
        {'name': 'Digital Marketplace', 'framework': 'dm', 'status': 'pending', 'slug': 'digital-marketplace'},
    ])

    op.bulk_insert(models.FrameworkLot.__table__, [
        {'framework_id': 7, 'lot_id': 9},
        {'framework_id': 7, 'lot_id': 10}

    ])


def downgrade():
    pass
