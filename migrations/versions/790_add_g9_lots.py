"""add entries to lots table for G-Cloud 9

Revision ID: 790
Revises: 780
Create Date: 2017-01-27 13:33:33.333333

"""

# revision identifiers, used by Alembic.
revision = '790'
down_revision = '780'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


def upgrade():
    # Insert G-Cloud 9 lot records

    lot_table = table(
        'lots',
        column('name', sa.String),
        column('slug', sa.String),
        column('one_service_limit', sa.Boolean),
        column('data', sa.JSON)
    )

    op.bulk_insert(lot_table, [
        {
            'name': 'Cloud hosting', 'slug': 'cloud-hosting', 'one_service_limit': False,
            'data': {"unitSingular": "service", "unitPlural": "services"}
        },
        {
            'name': 'Cloud software', 'slug': 'cloud-software', 'one_service_limit': False,
            'data': {"unitSingular": "service", "unitPlural": "services"}
        },
        {
            'name': 'Cloud support', 'slug': 'cloud-support', 'one_service_limit': False,
            'data': {"unitSingular": "service", "unitPlural": "services"}
        },
    ])


def downgrade():

    op.execute("""
        DELETE from lots WHERE slug in ('cloud-hosting', 'cloud-software', 'cloud-support');
    """)
