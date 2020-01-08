"""lots: add id/one_service_limit unique constraint

Revision ID: 1430
Revises: 1420
Create Date: 2020-01-08 11:35:28.932921

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1430'
down_revision = '1420'


def upgrade():
    op.create_unique_constraint('uq_lots_id_one_service_limit', 'lots', ['id', 'one_service_limit'])


def downgrade():
    op.drop_constraint('uq_lots_id_one_service_limit', 'lots', type_='unique')
