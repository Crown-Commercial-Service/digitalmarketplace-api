"""Create archives for current service versions

Revision ID: 60_archive_current_services
Revises: 50_remove_updated_details
Create Date: 2015-06-16 14:47:45.802476

"""

# revision identifiers, used by Alembic.
revision = '60_archive_current_services'
down_revision = '50_remove_updated_details'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute(
        """
        INSERT INTO archived_services (
            framework_id,
            service_id,
            supplier_id,
            created_at,
            updated_at,
            data,
            status
        ) SELECT
            framework_id,
            service_id,
            supplier_id,
            created_at,
            updated_at,
            data,
            status
        FROM services;
        """
    )


def downgrade():
    pass
