"""Extract service lot into lot_id column

Revision ID: 340
Revises: 330
Create Date: 2015-10-14 11:50:12.505032

"""

# revision identifiers, used by Alembic.
revision = '340'
down_revision = '330'

from alembic import op
import sqlalchemy as sa


def upgrade():
    for table in ['services', 'archived_services', 'draft_services']:
        op.execute("""
            UPDATE {table} SET lot_id = lots.id
            FROM framework_lots, lots
            WHERE
                framework_lots.framework_id = {table}.framework_id
                AND framework_lots.lot_id = lots.id
                AND (
                    lower({table}.data->>'lot') = lots.slug
                    OR (
                        {table}.data->>'lot' = 'missing'
                        AND lots.slug = 'scs'
                  )
                )
        """.format(table=table))

    op.alter_column('archived_services', 'lot_id', existing_type=sa.BIGINT(), nullable=False)
    op.alter_column('draft_services', 'lot_id', existing_type=sa.BIGINT(), nullable=False)
    op.alter_column('services', 'lot_id', existing_type=sa.BIGINT(), nullable=False)


def downgrade():
    op.alter_column('services', 'lot_id', existing_type=sa.BIGINT(), nullable=True)
    op.alter_column('draft_services', 'lot_id', existing_type=sa.BIGINT(), nullable=True)
    op.alter_column('archived_services', 'lot_id', existing_type=sa.BIGINT(), nullable=True)
