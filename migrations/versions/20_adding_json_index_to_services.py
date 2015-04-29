"""empty message

Revision ID: 10_adding_supplier_to_user_table
Revises: 550715127385
Create Date: 2015-04-21 07:45:29.958447

"""

# revision identifiers, used by Alembic.
revision = '20_adding_json_index_to_services'
down_revision = '10_adding_supplier_to_user_table'

from alembic import op
from sqlalchemy import text


def upgrade():
    op.create_index('ix_service_ordering', 'services', [text("framework_id, (data->>'lot'), (data->>'serviceName')")])


def downgrade():
    op.drop_index(op.f('ix_service_ordering'), table_name='services')
