"""Set User roles type to Enum

Revision ID: 250_enum_user_role
Revises: 241_duns_number_unique_again
Create Date: 2015-08-17 17:42:14.401470

"""

# revision identifiers, used by Alembic.
revision = '250_enum_user_role'
down_revision = '241_duns_number_unique_again'

from alembic import op
import sqlalchemy as sa


def upgrade():
    role_enum = sa.Enum('buyer', 'supplier', 'admin', name='user_roles_enum')
    role_enum.create(op.get_bind(), checkfirst=False)

    op.execute('ALTER TABLE users ALTER COLUMN role TYPE user_roles_enum USING role::user_roles_enum')

    op.alter_column(
        'users', 'role',
        type_=role_enum,
        existing_type=sa.String(),
    )

    op.drop_constraint('ck_user_supplier_has_supplier_id', 'users', type_='check')


def downgrade():
    op.alter_column(
        'users', 'role',
        type_=sa.String(),
        existing_type=sa.Enum('buyer', 'supplier', 'admin', name='user_roles_enum'),
    )

    op.create_check_constraint(
        "ck_user_supplier_has_supplier_id",
        "users",
        "((role='buyer') or (role='admin') or (role = 'supplier'  and supplier_id is not null))"
    )
