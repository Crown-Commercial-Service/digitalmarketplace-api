"""draft services: add lot_one_service_limit column

Revision ID: 1410
Revises: 1400
Create Date: 2020-01-07 15:55:53.583221

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1410'
down_revision = '1400'


def upgrade():
    op.add_column(
        'draft_services',
        sa.Column('lot_one_service_limit', sa.Boolean(), nullable=True,),
    )


def downgrade():
    op.drop_column('draft_services', 'lot_one_service_limit')
