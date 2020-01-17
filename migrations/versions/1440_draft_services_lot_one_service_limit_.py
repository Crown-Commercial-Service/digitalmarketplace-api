"""draft_services.lot_one_service_limit: add constraints

Revision ID: 1440
Revises: 1430
Create Date: 2020-01-08 11:37:16.449391

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1440'
down_revision = '1430'


def upgrade():
    op.create_foreign_key(
        'fk_draft_services_lot_id_one_service_limit',
        'draft_services',
        'lots',
        ['lot_id', 'lot_one_service_limit'],
        ['id', 'one_service_limit'],
    )
    op.create_index(
        'idx_draft_services_enforce_one_service_limit',
        'draft_services',
        ['supplier_id', 'lot_id', 'framework_id'],
        unique=True,
        postgresql_where=sa.text('lot_one_service_limit'),
    )


def downgrade():
    op.drop_index('idx_draft_services_enforce_one_service_limit', table_name='draft_services')
    op.drop_constraint('fk_draft_services_lot_id_one_service_limit', 'draft_services', type_='foreignkey')
