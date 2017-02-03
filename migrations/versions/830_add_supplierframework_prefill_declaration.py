"""Add SupplierFramework.prefill_declaration_from_framework_id column and constraints

Revision ID: 830
Revises: 820
Create Date: 2017-02-02 14:18:54.512957

"""

# revision identifiers, used by Alembic.
revision = '830'
down_revision = '820'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('supplier_frameworks', sa.Column('prefill_declaration_from_framework_id', sa.Integer(), nullable=True))
    # manually truncated constraint name here to prevent postgres from truncating automatically
    op.create_foreign_key(op.f('fk_supplier_frameworks_prefill_declaration_from_framework_id'), 'supplier_frameworks', 'frameworks', ['prefill_declaration_from_framework_id'], ['id'])
    op.create_foreign_key(op.f('fk_supplier_frameworks_supplier_id_supplier_frameworks'), 'supplier_frameworks', 'supplier_frameworks', ['supplier_id', 'prefill_declaration_from_framework_id'], ['supplier_id', 'framework_id'])


def downgrade():
    op.drop_constraint(op.f('fk_supplier_frameworks_supplier_id_supplier_frameworks'), 'supplier_frameworks', type_='foreignkey')
    op.drop_constraint(op.f('fk_supplier_frameworks_prefill_declaration_from_framework_id'), 'supplier_frameworks', type_='foreignkey')
    op.drop_column('supplier_frameworks', 'prefill_declaration_from_framework_id')
