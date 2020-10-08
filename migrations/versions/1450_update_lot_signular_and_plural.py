"""update lot signular and plural

Revision ID: 1450
Revises: 1440
Create Date: 2020-10-07 11:09:41.713530

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '1450'
down_revision = '1440'


def upgrade():
    op.execute("""
        UPDATE lots
          SET data = '{"unitSingular": "research studio", "unitPlural": "research studios"}'
          WHERE slug = 'user-research-studios';
    """)

def downgrade():
    op.execute("""
        UPDATE lots
          SET data = '{"unitSingular": "lot", "unitPlural": "lots"}'
          WHERE slug = 'user-research-studios';
    """)

