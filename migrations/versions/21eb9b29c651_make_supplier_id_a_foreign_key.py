"""Make supplier_id a foreign key

Revision ID: 21eb9b29c651
Revises: 1e74a2d74d2d
Create Date: 2015-02-12 14:12:43.074568

"""

# revision identifiers, used by Alembic.
revision = '21eb9b29c651'
down_revision = '1e74a2d74d2d'

from alembic import op


def upgrade():
    op.create_foreign_key(None, 'services', 'suppliers', ['supplier_id'], ['supplier_id'])


def downgrade():
    op.drop_constraint(None, 'services', type_='foreignkey')
