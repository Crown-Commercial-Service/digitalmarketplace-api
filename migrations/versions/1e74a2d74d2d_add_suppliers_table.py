"""Add suppliers table

Revision ID: 1e74a2d74d2d
Revises: c8bce0740af
Create Date: 2015-02-12 14:02:10.416334

"""

# revision identifiers, used by Alembic.
revision = '1e74a2d74d2d'
down_revision = 'c8bce0740af'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suppliers_supplier_id'), 'suppliers', ['supplier_id'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_suppliers_supplier_id'), table_name='suppliers')
    op.drop_table('suppliers')
