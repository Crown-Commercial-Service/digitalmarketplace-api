"""empty message
Revision ID: 241_duns_number_unique_again
Revises: 240_duns_number_unique
Create Date: 2015-08-18 09:10:34.878708
"""

# revision identifiers, used by Alembic.
revision = '241_duns_number_unique_again'
down_revision = '240_duns_number_unique'

from alembic import op


def upgrade():
    op.drop_index('ix_suppliers_duns_number', table_name='suppliers')
    op.create_index(op.f('ix_suppliers_duns_number'), 'suppliers', ['duns_number'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_suppliers_duns_number'), table_name='suppliers')
    op.create_index('ix_suppliers_duns_number', 'suppliers', ['duns_number'], unique=False)
