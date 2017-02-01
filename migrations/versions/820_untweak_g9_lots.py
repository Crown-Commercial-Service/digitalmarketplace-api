"""no lots are products for G-Cloud 9 - they are all services

Revision ID: 820
Revises: 810
Create Date: 2017-02-01 11:20:00.000000

"""

# revision identifiers, used by Alembic.
revision = '820'
down_revision = '810'

from alembic import op


def upgrade():
    # Update G-Cloud 9 lot records

    op.execute("""
        UPDATE lots SET data = '{"unitSingular": "service", "unitPlural": "services"}'
        WHERE slug in ('cloud-hosting', 'cloud-software');
    """)


def downgrade():

    op.execute("""
            UPDATE lots SET data = '{"unitSingular": "product", "unitPlural": "products"}'
            WHERE slug in ('cloud-hosting', 'cloud-software');
        """)
