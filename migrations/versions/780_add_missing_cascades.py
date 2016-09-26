"""Add missing cascades

Revision ID: 780
Revises: 770
Create Date: 2016-09-26 09:50:51.052115

"""

# revision identifiers, used by Alembic.
revision = '780'
down_revision = '770'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint('supplier_user_invite_log_supplier_id_fkey1', 'supplier_user_invite_log', type_='foreignkey')
    op.create_foreign_key(
        'supplier_user_invite_log_supplier_id_fkey1',
        'supplier_user_invite_log',
        'supplier__contact',
        ('supplier_id', 'contact_id'),
        ('supplier_id', 'contact_id'),
        ondelete='cascade',
    )

    op.drop_constraint('user_supplier_code_fkey', 'user', type_='foreignkey')
    op.create_foreign_key(
        'user_supplier_code_fkey',
        'user',
        'supplier',
        ('supplier_code',),
        ('code',),
        ondelete='cascade',
    )


def downgrade():
    op.drop_constraint('supplier_user_invite_log_supplier_id_fkey1', 'supplier_user_invite_log', type_='foreignkey')
    op.create_foreign_key(
        'supplier_user_invite_log_supplier_id_fkey1',
        'supplier_user_invite_log',
        'supplier__contact',
        ('supplier_id', 'contact_id'),
        ('supplier_id', 'contact_id'),
    )

    op.drop_constraint('user_supplier_code_fkey', 'user', type_='foreignkey')
    op.create_foreign_key(
        'user_supplier_code_fkey',
        'user',
        'supplier',
        ('supplier_code',),
        ('code',),
    )
