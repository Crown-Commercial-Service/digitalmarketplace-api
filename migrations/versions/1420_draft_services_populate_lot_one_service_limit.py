"""draft services: populate lot_one_service_limit, set non-nullable

Revision ID: 1420
Revises: 1410
Create Date: 2020-01-07 16:14:04.461198

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1420'
down_revision = '1410'


def upgrade():
    op.execute(
        """UPDATE
            draft_services
        SET
            lot_one_service_limit = lots.one_service_limit
        FROM
            lots
        WHERE
            lots.id = draft_services.lot_id"""
    )
    op.alter_column(
        'draft_services',
        'lot_one_service_limit',
        existing_type=sa.BOOLEAN(),
        nullable=False,
    )


def downgrade():
    op.alter_column(
        'draft_services',
        'lot_one_service_limit',
        existing_type=sa.BOOLEAN(),
        nullable=True,
    )

