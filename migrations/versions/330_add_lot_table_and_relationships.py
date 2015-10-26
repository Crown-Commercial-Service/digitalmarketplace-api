"""Add lot table and relationships

Revision ID: 330
Revises: 320_drop_selection_answers
Create Date: 2015-10-14 10:48:29.311523

"""

# revision identifiers, used by Alembic.
revision = '330'
down_revision = '320_drop_selection_answers'

import itertools

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


def upgrade():
    # Create Lots table and Lot to Framework relationship
    op.create_table(
        'lots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('one_service_limit', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_lots_slug'), 'lots', ['slug'], unique=False)

    op.create_table(
        'framework_lots',
        sa.Column('framework_id', sa.Integer(), nullable=False),
        sa.Column('lot_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['framework_id'], ['frameworks.id'], ),
        sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], )
    )

    # Insert G-Cloud lot records
    lot_table = table(
        'lots',
        column('name', sa.String),
        column('slug', sa.String),
        column('one_service_limit', sa.Boolean)
    )

    op.bulk_insert(lot_table, [
        {'name': 'Software as a Service', 'slug': 'saas', 'one_service_limit': False},
        {'name': 'Platform as a Service', 'slug': 'paas', 'one_service_limit': False},
        {'name': 'Infrastructure as a Service', 'slug': 'iaas', 'one_service_limit': False},
        {'name': 'Specialist Cloud Services', 'slug': 'scs', 'one_service_limit': False},
    ])

    framework_lots_table = table(
        'framework_lots',
        column('framework_id', sa.Integer),
        column('lot_id', sa.Integer)
    )

    # Add 4 lots (ids 1-4) to all G-Cloud frameworks (ids 1-4)
    op.bulk_insert(framework_lots_table, [
        {'framework_id': framework_id, 'lot_id': lot_id}
        for framework_id, lot_id in itertools.product(range(1, 5), range(1, 5))
    ])

    op.add_column(u'archived_services', sa.Column('lot_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_archived_services_lot_id'), 'archived_services', ['lot_id'], unique=False)
    op.create_foreign_key(None, 'archived_services', 'lots', ['lot_id'], ['id'])

    op.add_column(u'draft_services', sa.Column('lot_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_draft_services_lot_id'), 'draft_services', ['lot_id'], unique=False)
    op.create_foreign_key(None, 'draft_services', 'lots', ['lot_id'], ['id'])

    op.add_column(u'services', sa.Column('lot_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_services_lot_id'), 'services', ['lot_id'], unique=False)
    op.create_foreign_key(None, 'services', 'lots', ['lot_id'], ['id'])


def downgrade():
    op.drop_constraint('services_lot_id_fkey', 'services', type_='foreignkey')
    op.drop_index(op.f('ix_services_lot_id'), table_name='services')
    op.drop_column(u'services', 'lot_id')

    op.drop_constraint('draft_services_lot_id_fkey', 'draft_services', type_='foreignkey')
    op.drop_index(op.f('ix_draft_services_lot_id'), table_name='draft_services')
    op.drop_column(u'draft_services', 'lot_id')

    op.drop_constraint('archived_services_lot_id_fkey', 'archived_services', type_='foreignkey')
    op.drop_index(op.f('ix_archived_services_lot_id'), table_name='archived_services')
    op.drop_column(u'archived_services', 'lot_id')

    op.drop_table('framework_lots')

    op.drop_index(op.f('ix_lots_slug'), table_name='lots')
    op.drop_table('lots')
