"""empty message

Revision ID: 10_adding_supplier_to_user_table
Revises: 550715127385
Create Date: 2015-04-21 07:45:29.958447

"""

# revision identifiers, used by Alembic.
revision = '10_adding_supplier_to_user_table'
down_revision = '550715127385'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('users', sa.Column('supplier_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_users_supplier_id'), 'users', ['supplier_id'], unique=False)
    op.create_foreign_key(None, 'users', 'suppliers', ['supplier_id'], ['supplier_id'])

    op.create_check_constraint(
        "ck_user_supplier_has_supplier_id",
        "users",
        "((role='buyer') or (role='admin') or (role = 'supplier'  and supplier_id is not null))"
    )

    op.drop_constraint('ck_users_role', 'users', type_='check')


def downgrade():
    op.drop_constraint('users_supplier_id_fkey', 'users', type_='foreignkey')
    op.drop_constraint('ck_user_supplier_has_supplier_id', 'users', type_='check')
    op.drop_index(op.f('ix_users_supplier_id'), table_name='users')
    op.drop_column('users', 'supplier_id')
