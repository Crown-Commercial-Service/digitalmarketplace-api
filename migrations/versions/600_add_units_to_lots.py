"""Add units to lots, for display by the frontend aps

Revision ID: 600
Revises: 590
Create Date: 2016-05-05 10:49:45.258601

"""

# revision identifiers, used by Alembic.
revision = '600'
down_revision = '590'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('lots', sa.Column('data', postgresql.JSON(), nullable=True))
    op.execute("""
        UPDATE lots
          SET data = '{"unitSingular": "service", "unitPlural": "services"}'
          WHERE  slug in ('saas', 'paas', 'iaas', 'scs', 'digital-outcomes', 'digital-specialists', 'user-research-participants');
    """)
    op.execute("""
        UPDATE lots
          SET data = '{"unitSingular": "lab", "unitPlural": "labs"}'
          WHERE  slug = 'user-research-studios';
    """)


def downgrade():
    op.drop_column('lots', 'data')
