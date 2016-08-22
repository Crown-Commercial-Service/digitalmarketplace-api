"""empty message

Revision ID: 5572dc54a164
Revises: 700
Create Date: 2016-08-22 10:46:55.311958

"""

# revision identifiers, used by Alembic.
revision = '710'
down_revision = '700'

from alembic import op
import sqlalchemy as sa


def upgrade():
    from app import models
    op.bulk_insert(models.Lot.__table__, [
         {'slug': 'digital-outcome', 'name': 'Digital outcome', 'one_service_limit': 'true',
         'data': {"unitSingular": "service", "unitPlural": "services"}}
    ])
    op.bulk_insert(models.FrameworkLot.__table__, [
        {'framework_id': 6, 'lot_id': 10}
    ])


def downgrade():
    pass
