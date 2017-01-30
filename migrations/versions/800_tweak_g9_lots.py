"""some lots are products for G-Cloud 9

Revision ID: 800
Revises: 790
Create Date: 2017-01-30 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = '800'
down_revision = '790'

from alembic import op


def upgrade():
    # Update G-Cloud 9 lot records

    op.execute("""
        UPDATE lots SET data = '{"unitSingular": "product", "unitPlural": "products"}'
        WHERE slug in ('cloud-hosting', 'cloud-software');
    """
)


def downgrade():

    op.execute("""
        UPDATE lots SET data = '{"unitSingular": "service", "unitPlural": "services"}'
        WHERE slug in ('cloud-hosting', 'cloud-software');
    """)
