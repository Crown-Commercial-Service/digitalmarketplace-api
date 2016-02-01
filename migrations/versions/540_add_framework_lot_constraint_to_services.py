"""Add framework lot constraint to services

Revision ID: 540
Revises: 530
Create Date: 2016-01-26 14:22:07.624062

"""

# revision identifiers, used by Alembic.
revision = '540'
down_revision = '530'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_foreign_key('archived_services_framework_id_fkey1', 'archived_services', 'framework_lots', ['framework_id', 'lot_id'], ['framework_id', 'lot_id'])
    op.create_foreign_key('draft_services_framework_id_fkey1', 'draft_services', 'framework_lots', ['framework_id', 'lot_id'], ['framework_id', 'lot_id'])
    op.create_foreign_key('services_framework_id_fkey1', 'services', 'framework_lots', ['framework_id', 'lot_id'], ['framework_id', 'lot_id'])


def downgrade():
    op.drop_constraint('services_framework_id_fkey1', 'services', type_='foreignkey')
    op.drop_constraint('draft_services_framework_id_fkey1', 'draft_services', type_='foreignkey')
    op.drop_constraint('archived_services_framework_id_fkey1', 'archived_services', type_='foreignkey')
