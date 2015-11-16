"""add entries to lots table for DOS

Revision ID: 430
Revises: 420
Create Date: 2015-11-16 11:34:41.412730

"""

# revision identifiers, used by Alembic.
revision = '430'
down_revision = '420'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


def upgrade():
    # Insert DOS lot records

    lot_table = table(
        'lots',
        column('name', sa.String),
        column('slug', sa.String),
        column('one_service_limit', sa.Boolean)
    )

    op.bulk_insert(lot_table, [
        {'name': 'Digital outcomes', 'slug': 'digital-outcomes', 'one_service_limit': True},
        {'name': 'Digital specialists', 'slug': 'digital-specialists', 'one_service_limit': True},
        {'name': 'User research studios', 'slug': 'user-research-studios',
         'one_service_limit': False},
        {'name': 'User research participants', 'slug': 'user-research-participants',
         'one_service_limit': True},
    ])

    conn = op.get_bind()
    res = conn.execute("SELECT id FROM frameworks WHERE slug = 'digital-outcomes-and-specialists'")
    framework = list(res.fetchall())

    res = conn.execute("SELECT id FROM lots WHERE slug in ('digital-outcomes'," +
                       "'digital-specialists', 'user-research-studios'," +
                       " 'user-research-participants')")
    lots = list(res.fetchall())

    if len(framework) == 0:
        raise Exception("Framework not found")

    for lot in lots:
        op.execute("INSERT INTO framework_lots (framework_id, lot_id) VALUES({}, {})".format(
            framework[0]["id"], lot["id"]))


def downgrade():
    conn = op.get_bind()
    res = conn.execute("SELECT id FROM frameworks WHERE slug = 'digital-outcomes-and-specialists'")
    framework = list(res.fetchall())

    op.execute("""
        DELETE FROM framework_lots WHERE framework_id={}
    """.format(framework[0]['id']))

    op.execute("""
        DELETE from lots WHERE slug in ('digital-outcomes', 'digital-specialists',
         'user-research-studios', 'user-research-participants');
    """)
