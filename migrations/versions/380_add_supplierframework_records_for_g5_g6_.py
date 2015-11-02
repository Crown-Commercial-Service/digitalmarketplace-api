"""Add SupplierFramework records for G5, G6 suppliers

Revision ID: 380
Revises: 370_use_sqlalchemy_validator
Create Date: 2015-11-02 16:27:01.538066

"""

# revision identifiers, used by Alembic.
revision = '380'
down_revision = '370_use_sqlalchemy_validator'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
        INSERT INTO supplier_frameworks
            (supplier_id, framework_id)
        SELECT DISTINCT supplier_id, framework_id
            FROM services
                WHERE framework_id in (1, 3)
    """)


def downgrade():
    op.execute("""
        DELETE from supplier_frameworks WHERE framework_id in (1, 3)
    """)
